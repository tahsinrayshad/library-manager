"""Domain model package for library-manager.

This file exists to make `models` an explicit, regular package rather than an
implicit namespace package. The code imported correctly without it, because
Python 3.3 and later synthesise namespace packages automatically, but static
tooling does not always follow that synthesis:

  * `pyreverse` failed outright with "No module named models.__init__" when
    pointed at the package directory, analysed only 2 of the 4 modules, and
    still emitted a well-formed class diagram that silently omitted both
    `Book` and `Library`.
  * With the modules named explicitly it resolved them inconsistently between
    runs, as top-level `book`/`library` on one run and `models.book`/
    `models.library` on another, producing different dependency graphs from
    identical source.

An empty marker file costs nothing at runtime and makes the package boundary
unambiguous to every tool that reads the source rather than importing it.
"""

from models.book import Book
from models.library import Library

__all__ = ["Book", "Library"]
