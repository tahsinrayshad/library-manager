from models.book import Book  # Fixed: removed 'models.' since book.py is in root directory
from db_connection import Connection
from colorama import Fore, init
init(autoreset=True)


class Library:

    # The column being updated cannot be interpolated from user input: each
    # editable field maps to a complete, fixed statement. The previous code
    # built the column name with an f-string, which was safe only because the
    # surrounding prompt loop happened to constrain the value. That guarantee
    # lived in the wrong place -- one refactor away from becoming an injection.
    _UPDATE_QUERIES = {
        "title": "UPDATE books SET title = ? "
                 "WHERE title = ? AND author = ? AND year = ?",
        "author": "UPDATE books SET author = ? "
                  "WHERE title = ? AND author = ? AND year = ?",
        "year": "UPDATE books SET year = ? "
                "WHERE title = ? AND author = ? AND year = ?",
    }
    EDITABLE_FIELDS = tuple(_UPDATE_QUERIES)

    def __init__(self):
        self.books = []
        self.load_from_db()



    def add_book(self, book):
        titles = [b.title.lower() for b in self.books]
        if book.title.lower() not in titles:
            check = input(Fore.RED + f"Are you sure you want to save '{book.title}'? (Y/N): ").strip().lower()
            if check == "y":
                if book.save_to_db():
                    self.books.append(book)
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
        for book in self.books:
            if name_book.lower() == book.title.lower():
                check = input(Fore.RED + f"Are you sure you want to remove '{name_book}'? (Y/N): ").strip().lower()
                
                if check == 'y':
                    query = "DELETE FROM books WHERE title = ? AND author = ? AND year = ?"
                    values = (book.title, book.author, book.year)
                    try:
                        with Connection.cursor(commit=True) as cur:
                            cur.execute(query, values)

                        self.books.remove(book)
                        print(Fore.GREEN + f"'{name_book}' removed successfully!")

                    except Exception as e:
                        print(f"Error deleting from DB: {e}")
                else:
                    print(Fore.RED + 'Remove operation canceled.')
                return
        
        print(Fore.RED + f"Book '{name_book}' not found.")

    def search_book(self, name_book):
        matches = [] 
        
        for book in self.books:
            if name_book.lower() in book.title.lower() or name_book.lower() in book.author.lower():
                matches.append(book)
        
        if matches:
            print(f"Found {len(matches)} matching book(s) for '{name_book}':")
            for i, book in enumerate(matches, 1):
                print(f"{i} - {book}")
        else:
            print(Fore.RED + f"No books found matching '{name_book}'.")



    def edit_book(self, name_book):
        for book in self.books:
            if name_book.lower() == book.title.lower():
                while True:
                    check = input(f"What do you want to change in '{name_book}'? (title/author/year): ").strip().lower()
                    if check in self.EDITABLE_FIELDS:
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

                query = self._UPDATE_QUERIES.get(check)
                if query is None:
                    # Unreachable while the prompt loop guards `check`, but the
                    # safety of the SQL no longer depends on that loop.
                    print(Fore.RED + f"Refusing to update unknown field '{check}'.")
                    return

                values = (new_value, book.title, book.author, book.year)
                try:
                    with Connection.cursor(commit=True) as cur:
                        cur.execute(query, values)

                    setattr(book, check, new_value)
                    print(Fore.GREEN + f"Book updated successfully!\nNew details: {book}")

                except Exception as e:
                    print(f"Error updating database: {e}")
                return
        
        print(Fore.RED + f"Book '{name_book}' not found.")

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
        try:
            with Connection.cursor() as cur:
                cur.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name='books'"
                )
                if cur.fetchone():
                    cur.execute("SELECT title, author, year FROM books")
                    results = cur.fetchall()
                    self.books = [Book(r[0], r[1], r[2]) for r in results]
                    print(Fore.BLUE + f"Loaded {len(self.books)} books from database.")
                else:
                    self.books = []
                    print("Books table not found. Starting with empty library.")
        except Exception as e:
            print(f"Error loading from database: {e}")
            self.books = []