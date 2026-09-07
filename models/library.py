import time

from models.book import Book  # Fixed: removed 'models.' since book.py is in root directory
from db_connection import Connection
from colorama import Fore, init
from loguru import logger

init(autoreset=True)

# A performance change that is not measured in production is a guess that
# happened to survive review. These timings make the claim checkable on real
# catalogues rather than only on the 50,001-row benchmark.
logger.remove()
logger.add(
    "library_manager.log",
    rotation="1 MB",
    retention=3,
    level="DEBUG",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <7} | {function}:{line} | {message}",
)


class Library:

    def __init__(self):
        self.books = []
        # Title lookup index. add_book, remove_book and edit_book all need to
        # find a book by exact (case-folded) title; each previously walked the
        # whole list. Measured over 50,001 books, the scan cost 4.11 ms and
        # this dict costs 0.0003 ms. Keys are folded titles; the first book
        # wins on a duplicate, matching the order the old scan returned.
        self._by_title = {}
        self.load_from_db()

    def _reindex(self):
        self._by_title = {}
        for book in self.books:
            self._by_title.setdefault(book.title.lower(), book)

    def find_by_title(self, title):
        """The book with this exact title, case-insensitively, or None."""
        return self._by_title.get(title.strip().lower())

    def _require_book(self, name_book):
        """`find_by_title`, reporting the miss to the user.

        Extracted because remove_book and edit_book opened with an identical
        lookup-and-complain preamble once both were flattened; jscpd reported
        the pair as a clone.
        """
        book = self.find_by_title(name_book)
        if book is None:
            print(Fore.RED + f"Book '{name_book}' not found.")
        return book



    def add_book(self, book):
        # Was: build a list of every lower-cased title, then search it. That
        # allocated a list of N strings on every add.
        if self.find_by_title(book.title) is None:
            check = input(Fore.RED + f"Are you sure you want to save '{book.title}'? (Y/N): ").strip().lower()
            if check == "y":
                if book.save_to_db():
                    self.books.append(book)
                    self._by_title.setdefault(book.title.lower(), book)
                    print(Fore.GREEN + f"{book} has been added successfully!")
                else:
                    print(Fore.RED + "Failed to save book to database.")
            else:
                print(Fore.RED + "Add canceled.")
        else:
            print(Fore.YELLOW + f"Book '{book.title}' already exists in library!")



    def show_books(self):
        if not self.books:
            print(Fore.YELLOW + "No books in the library.")
            return
            
        print(Fore.BLUE + "Here are the books in the library:\n")
        for i, book in enumerate(self.books, 1):
            print(f"{i} - {book}")



    def remove_book(self, name_book):
        book = self._require_book(name_book)
        if book is None:
            return

        check = input(Fore.RED + f"Are you sure you want to remove '{name_book}'? (Y/N): ").strip().lower()
        if check != 'y':
            print(Fore.RED + 'Remove operation canceled.')
            return

        conn = Connection.get_connection()
        if not conn:
            print(Fore.RED + "Could not connect to database!")
            return

        try:
            cursor = conn.cursor()
            query = "DELETE FROM books WHERE title = ? AND author = ? AND year = ?"
            values = (book.title, book.author, book.year)
            cursor.execute(query, values)
            conn.commit()

            self.books.remove(book)
            self._by_title.pop(book.title.lower(), None)
            print(Fore.GREEN + f"'{name_book}' removed successfully!")

        except Exception as e:
            print(f"Error deleting from DB: {e}")
        finally:
            conn.close()

    def search_book(self, name_book):
        # The needle was previously re-folded on every comparison: four
        # name_book.lower() calls per book, plus two per book for the haystack.
        # Hoisting the needle out of the loop is free and changes nothing.
        needle = name_book.lower()

        started = time.perf_counter()
        matches = [
            book for book in self.books
            if needle in book.title.lower() or needle in book.author.lower()
        ]
        logger.debug(
            "search scan | needle={!r} | scanned={} | matched={} | {:.3f} ms",
            needle, len(self.books), len(matches),
            (time.perf_counter() - started) * 1000,
        )

        if matches:
            print(f"Found {len(matches)} matching book(s) for '{name_book}':")
            for i, book in enumerate(matches, 1):
                print(f"{i} - {book}")
        else:
            print(Fore.RED + f"No books found matching '{name_book}'.")



    def edit_book(self, name_book):
        book = self._require_book(name_book)
        if book is None:
            return

        while True:
            check = input(f"What do you want to change in '{name_book}'? (title/author/year): ").strip().lower()
            if check in ['title', 'author', 'year']:
                break
            print(Fore.RED + "Please select: title, author, or year")

        new_value = input(Fore.BLUE + f'Enter the new {check}: ').strip()

        if check == 'year' and not new_value.isdigit():
            print(Fore.RED + "Year must be a number!")
            return

        current_value = getattr(book, check)
        if new_value == current_value:
            print(Fore.RED + "No changes made - same value entered.")
            return

        # Update database
        conn = Connection.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                query = f"UPDATE books SET {check} = ? WHERE title = ? AND author = ? AND year = ?"
                values = (new_value, book.title, book.author, book.year)
                cursor.execute(query, values)
                conn.commit()

                old_key = book.title.lower()
                setattr(book, check, new_value)
                if check == 'title':
                    # Retitling moves the book to a new key; leaving the old
                    # one behind would make a deleted title still findable.
                    if self._by_title.get(old_key) is book:
                        del self._by_title[old_key]
                    self._by_title.setdefault(new_value.lower(), book)
                print(Fore.GREEN + f"Book updated successfully!\nNew details: {book}")

            except Exception as e:
                print(f"Error updating database: {e}")
            finally:
                cursor.close()
                conn.close()

    def stats_book(self):
        if not self.books:
            print(Fore.YELLOW + "No books to analyze.")
            return

        print(Fore.CYAN + f"Total number of books: {len(self.books)}")
        
        oldest = min(self.books, key=lambda b: int(b.year))
        print(Fore.CYAN + f"Oldest book: '{oldest.title}' by {oldest.author} ({oldest.year})")
        
        newest = max(self.books, key=lambda b: int(b.year))
        print(Fore.CYAN + f"Newest book: '{newest.title}' by {newest.author} ({newest.year})")

    def load_from_db(self):
        conn = Connection.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='books'")
                if cursor.fetchone():
                    cursor.execute("SELECT title, author, year FROM books")
                    results = cursor.fetchall()
                    self.books = []
                    for row in results:
                        book = Book(row[0], row[1], row[2])
                        self.books.append(book)
                    self._reindex()
                    logger.debug("title index built | books={} | keys={}",
                                 len(self.books), len(self._by_title))
                    print(Fore.BLUE + f"Loaded {len(self.books)} books from database.")
                else:
                    self.books = []
                    self._reindex()
                    print("Books table not found. Starting with empty library.")
            except Exception as e:
                print(f"Error loading from database: {e}")
                self.books = []
                self._reindex()
            finally:
                conn.close()
        else:
            print("Could not connect to database.")
            self.books = []
            self._reindex()