"""SQLite database connection and lifecycle manager."""

import sqlite3
from pathlib import Path
from typing import Generator
import contextlib

from src.core.logging import logger


class Database:
    """Manages SQLite database connections and schema migrations."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._schema_file = Path(__file__).parent / "schema.sql"

    def get_connection(self) -> sqlite3.Connection:
        """Returns a configured SQLite connection with foreign keys and Row factory."""
        conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=30.0,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    @contextlib.contextmanager
    def session(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager providing an auto-committing transactional connection."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as exc:
            conn.rollback()
            logger.error("Database transaction rolled back due to error: %s", exc)
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        """Applies schema DDL if tables do not exist."""
        if not self._schema_file.exists():
            raise FileNotFoundError(f"Schema file not found at {self._schema_file}")

        with open(self._schema_file, "r", encoding="utf-8") as f:
            schema_ddl = f.read()

        with self.session() as conn:
            conn.executescript(schema_ddl)

        logger.info("Database schema initialized successfully at %s", self.db_path)

