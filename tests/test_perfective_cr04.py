"""Tests for CR-04: the in-memory title index.

The index is a cache, and a cache that drifts out of step with the data it
describes is worse than no cache at all. These tests pin the invariant that
`_by_title` always agrees with `books` after every mutating operation.
"""

from models.book import Book
from models.library import Library


def test_find_by_title_is_case_and_whitespace_insensitive(db):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()
    assert lib.find_by_title("Dune") is not None
    assert lib.find_by_title("DUNE") is not None
    assert lib.find_by_title("  dune  ") is not None


def test_find_by_title_returns_none_when_absent(db):
    assert Library().find_by_title("Nothing") is None


def test_index_agrees_with_list_after_load(db):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    Book("Emma", "Jane Austen", 1815).save_to_db()
    lib = Library()
    assert set(lib._by_title) == {b.title.lower() for b in lib.books}


def test_index_updated_after_add(db, answers):
    lib = Library()
    answers.append("y")
    lib.add_book(Book("Dune", "Frank Herbert", 1965))
    assert lib.find_by_title("Dune") is lib.books[0]


def test_index_not_polluted_by_declined_add(db, answers):
    lib = Library()
    answers.append("n")
    lib.add_book(Book("Dune", "Frank Herbert", 1965))
    assert lib.find_by_title("Dune") is None
    assert lib._by_title == {}


def test_index_updated_after_remove(db, answers):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()
    answers.append("y")
    lib.remove_book("Dune")
    assert lib.find_by_title("Dune") is None
    assert set(lib._by_title) == {b.title.lower() for b in lib.books}


def test_index_intact_after_declined_remove(db, answers):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()
    answers.append("n")
    lib.remove_book("Dune")
    assert lib.find_by_title("Dune") is not None


def test_retitling_moves_the_index_key(db, answers):
    """The failure mode this test exists for: a stale key.

    If the old title is left in the index after a retitle, the book stays
    findable under a name it no longer has, and remove_book would then delete
    a row whose title no longer matches -- a silent no-op in SQL.
    """
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()
    answers.extend(["title", "Dune Messiah"])
    lib.edit_book("Dune")

    assert lib.find_by_title("Dune") is None, "stale key left behind"
    assert lib.find_by_title("Dune Messiah") is not None
    assert set(lib._by_title) == {b.title.lower() for b in lib.books}


def test_editing_a_non_title_field_leaves_the_key_alone(db, answers):
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    lib = Library()
    answers.extend(["year", "1966"])
    lib.edit_book("Dune")
    assert lib.find_by_title("Dune") is not None
    assert set(lib._by_title) == {b.title.lower() for b in lib.books}


def test_duplicate_titles_resolve_to_the_first_as_the_old_scan_did(db):
    """Two rows can share a title: the schema has no uniqueness constraint.

    The previous linear scan returned the first match in insertion order, so
    the index must too.
    """
    Book("Dune", "Frank Herbert", 1965).save_to_db()
    Book("Dune", "Someone Else", 2001).save_to_db()
    lib = Library()
    assert len(lib.books) == 2
    assert lib.find_by_title("Dune") is lib.books[0]
    assert lib.find_by_title("Dune").author == "Frank Herbert"


def test_search_still_matches_substrings_case_insensitively(db, capsys):
    Book("Nineteen Eighty-Four", "George Orwell", 1949).save_to_db()
    lib = Library()
    lib.search_book("ORWELL")
    assert "Nineteen Eighty-Four" in capsys.readouterr().out
    lib.search_book("eighty")
    assert "Nineteen Eighty-Four" in capsys.readouterr().out
