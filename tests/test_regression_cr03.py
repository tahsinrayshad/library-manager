"""Regression tests for CR-03 (preventive hardening).

Unlike the characterisation suite, these tests assert the behaviour the system
*should* have. They are expected to fail against the unmodified code and to
pass after the preventive change; that transition is the evidence that the
change did something real.
"""

import sqlite3

import pytest

from db_connection import Connection
from models.book import Book
from models.library import Library


class CursorFailsConnection:
    """A connection whose cursor() fails, as a locked or corrupt file would."""

    def __init__(self):
        self.closed = False

    def cursor(self):
        raise sqlite3.OperationalError("database is locked")

    def commit(self):  # pragma: no cover - never reached
        raise AssertionError("commit() should not be reached")

    def close(self):
        self.closed = True


def test_edit_book_does_not_raise_nameerror_when_cursor_fails(
    db, answers, monkeypatch, capsys
):
    """`finally: cursor.close()` must not explode when cursor was never bound.

    models/library.py closes the cursor in a finally block, but `cursor` is
    only bound *inside* the try. If `conn.cursor()` itself raises, the finally
    clause dereferences an unbound local and raises NameError, which replaces
    the real database error with a misleading one and escapes the method's own
    exception handling entirely.
    """
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()
    answers.extend(["year", "1966"])

    bad = CursorFailsConnection()
    monkeypatch.setattr(Connection, "get_connection", staticmethod(lambda: bad))

    # Must not raise. The method is expected to report the database failure
    # and return, exactly as its own `except Exception` clause intends.
    lib.edit_book("Dune")

    out = capsys.readouterr().out
    assert "database is locked" in out, (
        "the real error should be reported to the user"
    )
    assert bad.closed, "the connection must still be closed"


def test_edit_book_only_accepts_known_columns(db, answers, monkeypatch):
    """The updatable column must come from a fixed set, not from user text.

    models/library.py builds its UPDATE with an f-string that interpolates the
    column name directly. Today the surrounding prompt loop happens to
    constrain that value to title/author/year, so it is not exploitable. The
    guarantee should not depend on the prompt loop: the column must be
    validated where the SQL is built.
    """
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()

    executed = []
    real_connect = Connection.get_connection

    # sqlite3.Connection and Cursor are C types whose methods are read-only,
    # so the recorder has to be a delegating wrapper rather than a patch.
    class RecordingCursor:
        def __init__(self, inner):
            self._inner = inner

        def execute(self, sql, *a, **kw):
            executed.append(sql)
            return self._inner.execute(sql, *a, **kw)

        def __getattr__(self, name):
            return getattr(self._inner, name)

    class RecordingConnection:
        def __init__(self, inner):
            self._inner = inner

        def cursor(self):
            return RecordingCursor(self._inner.cursor())

        def __getattr__(self, name):
            return getattr(self._inner, name)

    def spy_connection():
        return RecordingConnection(real_connect())

    monkeypatch.setattr(Connection, "get_connection", staticmethod(spy_connection))

    answers.extend(["year", "1966"])
    lib.edit_book("Dune")

    updates = [s for s in executed if s.strip().upper().startswith("UPDATE")]
    assert updates, "an UPDATE should have been issued"
    for sql in updates:
        column = sql.split("SET", 1)[1].split("=", 1)[0].strip()
        assert column in {"title", "author", "year"}, (
            f"column {column!r} was interpolated into SQL without validation"
        )
