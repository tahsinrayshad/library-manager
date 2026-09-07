# === CLI logic for managing the library system ===

from models.library import Library
from models.book import Book
from db_connection import Connection
from colorama import Fore, init
init(autoreset=True)


def show_help(commands):
    print(Fore.BLUE + "\n===== Library Management System =====")
    print(Fore.BLUE + "Available commands:")
    for cmd, desc in commands.items():
        print(Fore.BLUE + f"  {cmd:<10} - {desc}")
    print(Fore.BLUE + "=====================================\n")


def main():

    print(Fore.YELLOW + "\nInitializing database...")
    Connection.init_database()

    print(Fore.YELLOW + "\nChecking database connection...")
    con = Connection().get_connection()
    if con is None:
        print(Fore.RED + "Cannot start application without database connection!")
        print(Fore.YELLOW + "Please ensure:")
        print(Fore.YELLOW + "   • SQLite database file exists")
        print(Fore.YELLOW + "   • Database file has proper permissions")
        print(Fore.YELLOW + "   • Database schema is initialized\n")
        return
    else:
        print(Fore.GREEN + "Database connected successfully!")
        con.close()

    lib = Library()
    
    commands = {
        "add": "Add a new book",
        "show": "Display all books", 
        "edit": "Edit a book",
        "search": "Search for books",
        "remove": "Remove a book",
        "stats": "Show stats",
        "exit or x": "Exit the program",
        "clear": "Clear the content",
        "help add": "Show how to add books",
        "help remove": "Show how to remove books", 
        "help search": "Show how to search books",
        "help edit": "Show how to edit books"
    }

    try:
        while True:
            # `raw` preserves the user's capitalisation and is the only source
            # for operands; `command` is the case-folded copy used purely for
            # dispatch. Folding the whole line, as this once did, corrupted
            # every stored title and author.
            raw = input("\nEnter command (or 'help' for options): ").strip()
            command = raw.lower()

            if command.startswith("add "):
                args = raw[4:].strip()
                try:
                    import shlex
                    parts = shlex.split(args)
                    
                    if len(parts) == 3:
                        title, author, year_str = parts
                        try:
                            year = int(year_str)
                            if 1800 <= year <= 2025:
                                b = Book(title, author, year)
                                lib.add_book(b)
                                print(Fore.GREEN + f"Added: {title}")
                            else:
                                print(Fore.RED + "Enter a valid year (1800-2025)")
                        except ValueError:
                            print(Fore.RED + "Year must be a number")
                    else:
                        print(Fore.RED + 'Usage: add "Title" "Author" year')
                except ValueError:
                    print(Fore.RED + 'Usage: add "Title" "Author" year')
                    print(Fore.RED + 'Make sure to use quotes around title and author')

            elif command == "show":
                try:
                    lib.show_books()
                except:
                    print(Fore.RED + "Library is empty.")

            elif command == "stats":
                lib.stats_book()

            elif command.startswith("edit "):
                edit_term = raw[5:]
                if edit_term:
                    lib.edit_book(edit_term)
                else:
                    print(Fore.RED + "Usage: edit <term>")

            elif command.startswith("search "):
                search_term = raw[7:]
                if search_term:
                    lib.search_book(search_term)
                else:
                    print(Fore.RED + "Usage: search <term>")

            elif command.startswith("remove "):
                remove_term = raw[7:]
                if remove_term:
                    lib.remove_book(remove_term)
                else:
                    print(Fore.RED + "Usage: remove <term>")

            elif command == "help":
                show_help(commands)

            elif command == "help add":
                print(Fore.BLUE + "\n=== ADD COMMAND ===")
                print(Fore.BLUE + 'Usage: add "Title" "Author" year')
                print(Fore.BLUE + 'Example: add "1984" "George Orwell" 1949')
                print(Fore.BLUE + "===================")

            elif command == "help remove":
                print(Fore.BLUE + "\n=== REMOVE COMMAND ===")
                print(Fore.BLUE + "Usage: remove BookTitle")
                print(Fore.BLUE + "======================")

            elif command == "help search":
                print(Fore.BLUE + "\n=== SEARCH COMMAND ===")
                print(Fore.BLUE + "Usage: search term")
                print(Fore.BLUE + "======================")

            elif command == "help edit":
                print(Fore.BLUE + "\n=== EDIT COMMAND ===")
                print(Fore.BLUE + "Usage: edit BookTitle")
                print(Fore.BLUE + "Then follow prompts to change title/author/year")
                print(Fore.BLUE + "====================")

            elif command == "clear" or command == "cls":
                import os
                os.system('cls' if os.name == 'nt' else 'clear')

            elif command == "exit" or command == "x":
                print(Fore.CYAN + "\nExiting...")
                break

            else:
                print(Fore.RED + "\nUnknown command! Check 'help'")
                
    except KeyboardInterrupt:
        print(Fore.CYAN + "\nExiting...")
    except Exception as e:
        print(Fore.RED + f"Error: {e}")


if __name__ == "__main__":
    main()