import unittest

from library_cli.errors import ValidationError
from library_cli.service import add_copy, borrow_copy, register_reader, return_copy
from library_cli.storage import empty_library


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        data = add_copy(empty_library(), "C1", "Book", "Author")
        self.data = register_reader(data, "R1", "Reader")

    def test_copy_cannot_be_borrowed_twice(self) -> None:
        borrowed = borrow_copy(self.data, "C1", "R1", "2026-09-23")
        with self.assertRaises(ValidationError):
            borrow_copy(borrowed, "C1", "R1", "2026-09-24")

    def test_reader_cannot_borrow_more_than_five(self) -> None:
        data = self.data
        for number in range(2, 7):
            data = add_copy(data, f"C{number}", f"Book {number}", "Author")
        for number in range(1, 6):
            data = borrow_copy(data, f"C{number}", "R1", "2026-09-23")
        with self.assertRaises(ValidationError):
            borrow_copy(data, "C6", "R1", "2026-09-23")

    def test_return_date_cannot_precede_borrow_date(self) -> None:
        borrowed = borrow_copy(self.data, "C1", "R1", "2026-09-23")
        with self.assertRaises(ValidationError):
            return_copy(borrowed, "C1", "2026-09-22")

    def test_invalid_date_does_not_mutate_input(self) -> None:
        snapshot = repr(self.data)
        with self.assertRaises(ValidationError):
            borrow_copy(self.data, "C1", "R1", "23-09-2026")
        self.assertEqual(repr(self.data), snapshot)


if __name__ == "__main__":
    unittest.main()

