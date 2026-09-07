import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from colorama import Fore, init
from loguru import logger

init(autoreset=True)

# CR-02 was invisible at runtime: nothing reported which file was actually
# opened, so using the wrong database looked identical to using an empty one.
logger.remove()
logger.add(
    "library_manager.log",
    rotation="1 MB",
    retention=3,
    level="DEBUG",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <7} | {function}:{line} | {message}",
)

# The database used to be named by the bare relative string "library.db",
# which sqlite3 resolves against the process working directory rather than the
# project. Launching the application from anywhere other than the repository
# root therefore created a second, empty database instead of opening the real
# one. Anchoring to this module's own location makes the location stable no
# matter where the program is started from.
PROJECT_ROOT = Path(__file__).resolve().parent

# .env is optional. When it is absent, or the variable is unset, the defaults
# below apply and behaviour matches the historical layout.
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_DB_NAME = "library.db"
DB_PATH_ENV_VAR = "LIBRARY_DB_PATH"


def resolve_db_path():
    """Absolute path of the SQLite file, honouring LIBRARY_DB_PATH.

    A relative value is interpreted against the project root, not the working
    directory. An absolute value is used as given, so a deployment can place
    the database outside the source tree.
    """
    configured = os.getenv(DB_PATH_ENV_VAR, "").strip() or DEFAULT_DB_NAME
    path = Path(configured).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.debug(
        "database path resolved | source={} | configured={!r} | resolved={}",
        "env" if os.getenv(DB_PATH_ENV_VAR) else "default",
        configured,
        path,
    )
    return str(path)


class Connection:
    DB_NAME = resolve_db_path()

    @staticmethod
    def get_connection():
        try:
            conn = sqlite3.connect(Connection.DB_NAME)
            return conn
        except sqlite3.Error as e:
            print(Fore.RED + f"Database connection error: {e}")
            return None
    
    @staticmethod
    def init_database():
        conn = Connection.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS books (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        author TEXT NOT NULL,
                        year TEXT NOT NULL
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL
                    )
                ''')
                
                conn.commit()
                print(Fore.GREEN + "Database initialized successfully!")
                
            except sqlite3.Error as e:
                print(Fore.RED + f"Error initializing database: {e}")
            finally:
                conn.close()