import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from library_cli.cli import main


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "library.json"

    def run_cli(self, *arguments: str) -> tuple[int, str, str]:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["--data-file", str(self.path), *arguments])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_end_to_end_workflow(self) -> None:
        self.assertEqual(
            self.run_cli("add-copy", "C1", "海边的卡夫卡", "村上春树")[0], 0
        )
        self.assertEqual(self.run_cli("register-reader", "R1", "小林")[0], 0)
        self.assertEqual(self.run_cli("borrow", "C1", "R1", "2026-09-23")[0], 0)
        code, output, _ = self.run_cli("list", "--status", "borrowed")
        self.assertEqual(code, 0)
        self.assertIn("C1", output)
        self.assertIn("已借出", output)
        code, output, _ = self.run_cli("search", "村上", "--field", "author")
        self.assertEqual(code, 0)
        self.assertIn("海边的卡夫卡", output)
        self.assertEqual(self.run_cli("return", "C1", "2026-09-24")[0], 0)

    def test_failed_command_preserves_file(self) -> None:
        self.run_cli("add-copy", "C1", "Book", "Author")
        before = self.path.read_bytes()
        code, _, error = self.run_cli(
            "borrow", "C1", "missing", "2026-09-23"
        )
        self.assertNotEqual(code, 0)
        self.assertIn("不存在", error)
        self.assertEqual(self.path.read_bytes(), before)

    def test_json_is_human_readable_utf8(self) -> None:
        self.run_cli("add-copy", "C1", "三体", "刘慈欣")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 2)
        self.assertEqual(data["copies"]["C1"]["title"], "三体")


if __name__ == "__main__":
    unittest.main()
