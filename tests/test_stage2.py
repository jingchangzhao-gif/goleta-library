import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from library_cli.cli import main
from library_cli.errors import ValidationError
from library_cli.isbn import normalize_isbn


class StageTwoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.path = self.root / "library.json"

    def run_cli(self, *arguments: str) -> tuple[int, str, str]:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["--data-file", str(self.path), *arguments])
        return code, stdout.getvalue(), stderr.getvalue()

    def write_json(self, data: dict[str, object]) -> None:
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def test_legacy_data_is_read_without_rewrite_and_upgraded_on_write(self) -> None:
        self.write_json(
            {
                "copies": {"C1": {"title": "旧书", "author": "旧作者"}},
                "readers": {},
                "loans": [],
            }
        )
        before = self.path.read_bytes()
        code, output, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn("ISBN: -", output)
        self.assertEqual(self.path.read_bytes(), before)

        self.assertEqual(self.run_cli("register-reader", "R1", "读者")[0], 0)
        upgraded = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(upgraded["schema_version"], 2)
        self.assertIsNone(upgraded["copies"]["C1"]["isbn"])

    def test_unknown_future_schema_is_rejected_without_rewrite(self) -> None:
        self.write_json(
            {"schema_version": 3, "copies": {}, "readers": {}, "loans": []}
        )
        before = self.path.read_bytes()
        code, _, error = self.run_cli("list")
        self.assertNotEqual(code, 0)
        self.assertIn("未知版本 3", error)
        self.assertEqual(self.path.read_bytes(), before)

    def test_isbn_normalization_search_and_invalid_atomicity(self) -> None:
        code, _, _ = self.run_cli(
            "add-copy",
            "C1",
            "Book",
            "Author",
            "--isbn",
            "978-0-306-40615-7",
        )
        self.assertEqual(code, 0)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(data["copies"]["C1"]["isbn"], "9780306406157")
        code, output, _ = self.run_cli(
            "search", "978 0 306 40615 7", "--field", "isbn"
        )
        self.assertEqual(code, 0)
        self.assertIn("C1", output)
        self.assertIn("ISBN: 9780306406157", output)

        before = self.path.read_bytes()
        code, _, error = self.run_cli(
            "add-copy", "C2", "Bad", "Author", "--isbn", "9780306406158"
        )
        self.assertNotEqual(code, 0)
        self.assertIn("校验位", error)
        self.assertEqual(self.path.read_bytes(), before)

    def test_isbn_10_normalization_and_validation(self) -> None:
        self.assertEqual(normalize_isbn("0-8044-2957-x"), "080442957X")
        with self.assertRaises(ValidationError):
            normalize_isbn("0-8044-2957-0")

    def test_csv_dry_run_validates_all_rows_without_writing(self) -> None:
        self.run_cli("add-copy", "EXISTING", "Existing", "Author")
        csv_path = self.root / "valid.csv"
        csv_path.write_text(
            "copy_id,title,author,isbn\n"
            "C1,Book One,Author One,978-0-306-40615-7\n"
            "C2,Book Two,Author Two,\n",
            encoding="utf-8",
        )
        before = self.path.read_bytes()
        code, output, _ = self.run_cli("import-copies", str(csv_path), "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("第 2 行", output)
        self.assertIn("第 3 行", output)
        self.assertIn("将导入 2", output)
        self.assertEqual(self.path.read_bytes(), before)

    def test_csv_conflict_fails_entire_batch_without_rewrite(self) -> None:
        self.run_cli("add-copy", "EXISTING", "Existing", "Author")
        csv_path = self.root / "conflict.csv"
        csv_path.write_text(
            "copy_id,title,author,isbn\n"
            "C1,Book One,Author One,\n"
            "EXISTING,Conflict,Author Two,\n",
            encoding="utf-8",
        )
        before = self.path.read_bytes()
        code, _, error = self.run_cli("import-copies", str(csv_path))
        self.assertNotEqual(code, 0)
        self.assertIn("第 3 行", error)
        self.assertEqual(self.path.read_bytes(), before)

    def test_csv_duplicate_in_file_fails_entire_batch(self) -> None:
        self.run_cli("add-copy", "EXISTING", "Existing", "Author")
        csv_path = self.root / "duplicate.csv"
        csv_path.write_text(
            "copy_id,title,author,isbn\n"
            "C1,Book One,Author One,\n"
            "C1,Duplicate,Author Two,\n",
            encoding="utf-8",
        )
        before = self.path.read_bytes()
        code, _, error = self.run_cli("import-copies", str(csv_path))
        self.assertNotEqual(code, 0)
        self.assertIn("第 3 行", error)
        self.assertEqual(self.path.read_bytes(), before)

    def test_history_filters_and_stable_date_sort(self) -> None:
        self.write_json(
            {
                "schema_version": 2,
                "copies": {
                    "C1": {"title": "One", "author": "A", "isbn": None},
                    "C2": {"title": "Two", "author": "A", "isbn": None},
                    "C3": {"title": "Three", "author": "A", "isbn": None},
                },
                "readers": {"R1": {"name": "One"}, "R2": {"name": "Two"}},
                "loans": [
                    {
                        "copy_id": "C1",
                        "reader_id": "R1",
                        "borrowed_on": "2026-02-02",
                        "returned_on": "2026-02-03",
                    },
                    {
                        "copy_id": "C2",
                        "reader_id": "R2",
                        "borrowed_on": "2026-01-01",
                        "returned_on": None,
                    },
                    {
                        "copy_id": "C3",
                        "reader_id": "R1",
                        "borrowed_on": "2026-02-02",
                        "returned_on": None,
                    },
                ],
            }
        )
        code, output, _ = self.run_cli("history")
        self.assertEqual(code, 0)
        self.assertLess(output.index("C2"), output.index("C1"))
        self.assertLess(output.index("C1"), output.index("C3"))

        code, output, _ = self.run_cli("history", "--reader", "R1", "--status", "active")
        self.assertEqual(code, 0)
        self.assertIn("C3", output)
        self.assertNotIn("C1", output)
        self.assertNotIn("C2", output)

        code, _, error = self.run_cli("history", "--reader", "missing")
        self.assertNotEqual(code, 0)
        self.assertIn("不存在", error)


if __name__ == "__main__":
    unittest.main()
