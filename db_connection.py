import sqlite3
from contextlib import contextmanager

from colorama import Fore, init
from loguru import logger

init(autoreset=True)

# Centralising database access also centralises its observability: because
# every query now passes through Connection.cursor, one pair of log statements
# covers operations that were previously scattered across four modules.
logger.remove()
logger.add(
    "library_manager.log",
    rotation="1 MB",
    retention=3,
    level="DEBUG",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <7} | {function}:{line} | {message}",
)


class Connection:
    DB_NAME = "library.db"

    @staticmethod
    def get_connection():
        try:
            conn = sqlite3.connect(Connection.DB_NAME)
            return conn
        except sqlite3.Error as e:
            print(Fore.RED + f"Database connection error: {e}")
            return None

    @staticmethod
    @contextmanager
    def cursor(commit=False):
        """Yield a cursor, committing on success and always cleaning up.

        Every database operation in this project previously repeated the same
        connect / cursor / commit / ``finally: close()`` block, which is how
        the same bug came to exist in several places at once. Centralising it
        here means each call site expresses only its query.

        Cleanup is correct even when ``conn.cursor()`` itself fails: ``cur``
        is bound to None before the ``try``, so the ``finally`` clause can
        never dereference an unbound local.

        Raises ``sqlite3.Error`` so that callers can distinguish success from
        failure; the previous code swallowed errors inside each method.
        """
        conn = Connection.get_connection()
        if conn is None:
            raise sqlite3.OperationalError(
                f"could not open the database at {Connection.DB_NAME}"
            )
        cur = None
        try:
            cur = conn.cursor()
            yield cur
            if commit:
                conn.commit()
            logger.debug("db unit of work ok | commit={}", commit)
        except Exception as e:
            logger.error("db unit of work failed | commit={} | {}: {}",
                         commit, type(e).__name__, e)
            raise
        finally:
            if cur is not None:
                cur.close()
            conn.close()

    @staticmethod
    def init_database():
        try:
            with Connection.cursor(commit=True) as cur:
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS books (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        author TEXT NOT NULL,
                        year TEXT NOT NULL
                    )
                ''')

                cur.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL
                    )
                ''')

            print(Fore.GREEN + "Database initialized successfully!")

        except sqlite3.Error as e:
            print(Fore.RED + f"Error initializing database: {e}")