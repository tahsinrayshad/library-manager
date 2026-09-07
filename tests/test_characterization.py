"""Characterisation tests: the behaviour that must survive the refactor.

These tests describe what the application does today. They were written and
made to pass *before* any preventive change, so that the refactor could be
judged behaviour-preserving by running them again afterwards. They deliberately
assert current behaviour, including behaviour that is arguably wrong, because
the purpose of a safety net is to detect unintended change rather than to
express preference.
"""

from conftest import rows

from db_connection import Connection
from models.book import Book
from models.library import Library


# --------------------------------------------------------------------------
# Schema
# --------------------------------------------------------------------------

def test_init_database_creates_both_tables(db):
    import sqlite3

    conn = sqlite3.connect(str(db))
    try:
        names = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    finally:
        conn.close()
    assert {"books", "users"} <= names


def test_year_column_is_declared_text(db):
    import sqlite3

    conn = sqlite3.connect(str(db))
    try:
        cols = {r[1]: r[2] for r in conn.execute("PRAGMA table_info(books)")}
    finally:
        conn.close()
    # Recorded as-is: the application treats year as an integer but stores TEXT.
    assert cols["year"] == "TEXT"


# --------------------------------------------------------------------------
# Book
# --------------------------------------------------------------------------

def test_book_save_to_db_persists_a_row(db):
    assert Book("Dune", "Frank Herbert", 1965).save_to_db() is True
    assert rows(db) == [("Dune", "Frank Herbert", "1965")]


def test_book_str_and_repr(db):
    b = Book("Dune", "Frank Herbert", 1965)
    assert str(b) == "'Dune' by Frank Herbert (1965)"
    assert repr(b) == "Book(title='Dune', author='Frank Herbert', year='1965')"


def test_book_dict_roundtrip(db):
    b = Book("Dune", "Frank Herbert", 1965)
    assert Book.from_dict(b.to_dict()).to_dict() == b.to_dict()


# --------------------------------------------------------------------------
# Library.load_from_db
# --------------------------------------------------------------------------

def test_library_loads_existing_rows(db):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    Book("Emma", "Jane Austen", 1815).save_to_db()
    lib = Library()
    assert [b.title for b in lib.books] == ["Dune", "Emma"]


def test_library_is_empty_when_no_rows(db):
    assert Library().books == []


# --------------------------------------------------------------------------
# Library.add_book
# --------------------------------------------------------------------------

def test_add_book_confirmed_persists(db, answers):
    lib = Library()
    answers.append("y")
    lib.add_book(Book("Dune", "Frank Herbert", 1965))
    assert rows(db) == [("Dune", "Frank Herbert", "1965")]
    assert len(lib.books) == 1


def test_add_book_declined_persists_nothing(db, answers):
    lib = Library()
    answers.append("n")
    lib.add_book(Book("Dune", "Frank Herbert", 1965))
    assert rows(db) == []
    assert lib.books == []


def test_add_book_rejects_duplicate_title_case_insensitively(db, answers):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()
    # No input is queued: the duplicate check must short-circuit before
    # prompting, so any prompt here fails the test.
    lib.add_book(Book("DUNE", "Someone Else", 2001))
    assert rows(db) == [("Dune", "Frank Herbert", "1965")]


# --------------------------------------------------------------------------
# Library.remove_book
# --------------------------------------------------------------------------

def test_remove_book_confirmed(db, answers):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()
    answers.append("y")
    lib.remove_book("Dune")
    assert rows(db) == []
    assert lib.books == []


def test_remove_book_declined_keeps_row(db, answers):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()
    answers.append("n")
    lib.remove_book("Dune")
    assert rows(db) == [("Dune", "Frank Herbert", "1965")]


def test_remove_book_is_case_insensitive(db, answers):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()
    answers.append("y")
    lib.remove_book("DUNE")
    assert rows(db) == []


def test_remove_book_missing_title_is_a_no_op(db):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()
    lib.remove_book("Nonexistent")
    assert rows(db) == [("Dune", "Frank Herbert", "1965")]


# --------------------------------------------------------------------------
# Library.edit_book
# --------------------------------------------------------------------------

def test_edit_book_changes_year(db, answers):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()
    answers.extend(["year", "1966"])
    lib.edit_book("Dune")
    assert rows(db) == [("Dune", "Frank Herbert", "1966")]


def test_edit_book_changes_title(db, answers):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()
    answers.extend(["title", "Dune Messiah"])
    lib.edit_book("Dune")
    assert rows(db) == [("Dune Messiah", "Frank Herbert", "1965")]


def test_edit_book_changes_author(db, answers):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()
    answers.extend(["author", "F. Herbert"])
    lib.edit_book("Dune")
    assert rows(db) == [("Dune", "F. Herbert", "1965")]


def test_edit_book_reprompts_until_field_is_valid(db, answers):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()
    answers.extend(["publisher", "isbn", "year", "1966"])
    lib.edit_book("Dune")
    assert rows(db) == [("Dune", "Frank Herbert", "1966")]


def test_edit_book_rejects_non_numeric_year(db, answers):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()
    answers.extend(["year", "nineteen"])
    lib.edit_book("Dune")
    assert rows(db) == [("Dune", "Frank Herbert", "1965")]


def test_edit_book_same_value_makes_no_change(db, answers):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()
    answers.extend(["author", "Frank Herbert"])
    lib.edit_book("Dune")
    assert rows(db) == [("Dune", "Frank Herbert", "1965")]


def test_edit_book_missing_title_is_a_no_op(db):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()
    lib.edit_book("Nonexistent")
    assert rows(db) == [("Dune", "Frank Herbert", "1965")]


# --------------------------------------------------------------------------
# Library.search_book and stats_book
# --------------------------------------------------------------------------

def test_search_matches_title_and_author_case_insensitively(db, capsys):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    Book("Emma", "Jane Austen", 1815).save_to_db()
    lib = Library()

    lib.search_book("DUNE")
    assert "Dune" in capsys.readouterr().out

    lib.search_book("austen")
    assert "Emma" in capsys.readouterr().out


def test_search_reports_no_match(db, capsys):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()
    lib.search_book("zzz")
    assert "No books found" in capsys.readouterr().out


def test_stats_reports_oldest_and_newest(db, capsys):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    Book("Emma", "Jane Austen", 1815).save_to_db()
    lib = Library()
    lib.stats_book()
    out = capsys.readouterr().out
    assert "Total number of books: 2" in out
    assert "Emma" in out.split("Oldest book:")[1].split("\n")[0]
    assert "Dune" in out.split("Newest book:")[1].split("\n")[0]


def test_show_books_when_empty(db, capsys):
    Library().show_books()
    assert "No books in the library." in capsys.readouterr().out
