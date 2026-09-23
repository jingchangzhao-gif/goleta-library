import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from library_cli.cli import main


class PersistedLoanDateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "library.json"

    def write_data(self, borrowed_on: str, returned_on: str | None) -> None:
        data = {
            "schema_version": 2,
            "copies": {
                "C1": {"title": "Book", "author": "Author", "isbn": None}
            },
            "readers": {"R1": {"name": "Reader"}},
            "loans": [
                {
                    "copy_id": "C1",
                    "reader_id": "R1",
                    "borrowed_on": borrowed_on,
                    "returned_on": returned_on,
                }
            ],
        }
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def run_history(self) -> tuple[int, str, str]:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["--data-file", str(self.path), "history"])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_invalid_persisted_calendar_dates_are_rejected_without_rewrite(self) -> None:
        cases = (
            ("2026-02-30", None, "borrowed_on"),
            ("2026-02-28", "2026-02-30", "returned_on"),
        )
        for borrowed_on, returned_on, field_name in cases:
            with self.subTest(field_name=field_name):
                self.write_data(borrowed_on, returned_on)
                before = self.path.read_bytes()
                code, output, error = self.run_history()
                self.assertNotEqual(code, 0)
                self.assertEqual(output, "")
                self.assertIn(field_name, error)
                self.assertIn("YYYY-MM-DD", error)
                self.assertEqual(self.path.read_bytes(), before)

    def test_return_before_borrow_is_rejected_without_rewrite(self) -> None:
        self.write_data("2026-03-02", "2026-03-01")
        before = self.path.read_bytes()
        code, output, error = self.run_history()
        self.assertNotEqual(code, 0)
        self.assertEqual(output, "")
        self.assertIn("归还日期早于借阅日期", error)
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
