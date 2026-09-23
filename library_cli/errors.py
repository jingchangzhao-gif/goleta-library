class LibraryError(Exception):
    """Base exception for expected application failures."""


class ValidationError(LibraryError):
    """Raised when command input is invalid."""


class StorageError(LibraryError):
    """Raised when persisted library data cannot be read or written."""

