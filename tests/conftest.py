"""Shared fixtures for the library-manager test suite.

Every test runs against a throwaway SQLite file created from the application's
own schema, so the developer's real `library.db` is never touched.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from db_connection import Connection  # noqa: E402


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Redirect the application at a fresh database with the real schema."""
    path = tmp_path / "test.db"
    monkeypatch.setattr(Connection, "DB_NAME", str(path))
    Connection.init_database()
    return path


@pytest.fixture
def answers(monkeypatch):
    """Queue scripted replies for builtins.input.

    Returns a list; append the replies a test expects to be consumed, in
    order. An unexpected prompt fails the test rather than blocking on stdin.
    """
    queue = []

    def fake_input(prompt=""):
        if not queue:
            raise AssertionError(f"unexpected input() call: {prompt!r}")
        return queue.pop(0)

    monkeypatch.setattr("builtins.input", fake_input)
    return queue


def rows(db_path):
    """Every row in the books table, as (title, author, year) tuples."""
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute(
            "SELECT title, author, year FROM books ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
