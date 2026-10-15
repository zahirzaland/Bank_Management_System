"""SQLite connection management, transactions, backup and restore."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import config
from exceptions import ValidationError
from utils import utc_now_compact

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
REQUIRED_TABLES = {"staff_users", "customers", "accounts", "transactions", "audit_logs"}


class Database:
    """Owns one SQLite connection (the Tkinter app is single-threaded).

    The connection runs in autocommit mode; ``transaction()`` opens explicit
    BEGIN IMMEDIATE / COMMIT / ROLLBACK blocks so multi-step money movements
    succeed or fail together (FR-11, NFR-03). Nested use joins the outer block.
    """

    def __init__(self, path=":memory:"):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = self._connect(self.path)
        self._depth = 0

    @staticmethod
    def _connect(path: str) -> sqlite3.Connection:
        conn = sqlite3.connect(path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")  # must be enabled per connection
        return conn

    def initialize(self) -> None:
        self.conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(customers)")}
        migrations = {
            "kyc_status": "TEXT NOT NULL DEFAULT 'pending' CHECK (kyc_status IN ('pending', 'verified', 'rejected'))",
            "kyc_notes": "TEXT",
            "kyc_verified_at": "TEXT",
        }
        for name, definition in migrations.items():
            if name not in columns:
                self.conn.execute(f"ALTER TABLE customers ADD COLUMN {name} {definition}")

    def close(self) -> None:
        self.conn.close()

    @contextmanager
    def transaction(self):
        if self._depth:
            self._depth += 1
            try:
                yield self.conn
            finally:
                self._depth -= 1
            return
        self.conn.execute("BEGIN IMMEDIATE")
        self._depth = 1
        try:
            yield self.conn
            self.conn.execute("COMMIT")
        except BaseException:
            try:
                self.conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            self._depth = 0

    # ---- backup / restore (FR-19) ---------------------------------------
    def backup_to(self, destination) -> Path:
        dest = Path(destination)
        if self.path != ":memory:" and dest.resolve() == Path(self.path).resolve():
            raise ValidationError("Choose a backup file different from the live database.")
        dest.parent.mkdir(parents=True, exist_ok=True)
        target = sqlite3.connect(str(dest))
        try:
            self.conn.backup(target)  # SQLite online-backup API: consistent even while open
        finally:
            target.close()
        return dest

    @staticmethod
    def validate_backup_file(source) -> None:
        src = Path(source)
        if not src.is_file():
            raise ValidationError("The selected backup file does not exist.")
        try:
            conn = sqlite3.connect(src.resolve().as_uri() + "?mode=ro", uri=True)
            try:
                if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValidationError("The backup file failed the integrity check.")
                tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            finally:
                conn.close()
        except sqlite3.DatabaseError:
            raise ValidationError("The selected file is not a valid SQLite database.") from None
        if not REQUIRED_TABLES <= tables:
            raise ValidationError("The selected file is not a Bank Management System backup.")

    def restore_from(self, source) -> None:
        """Replace the live database contents with a validated backup."""
        if self._depth:
            raise RuntimeError("Cannot restore inside a transaction.")
        self.validate_backup_file(source)
        if self.path != ":memory:" and Path(source).resolve() == Path(self.path).resolve():
            raise ValidationError("Choose a backup file different from the live database.")
        if self.path != ":memory:" and Path(self.path).exists():
            config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            safety = config.BACKUP_DIR / f"pre_restore_{utc_now_compact()}.db"
            self.backup_to(safety)  # safety copy of the data about to be replaced
        src = sqlite3.connect(Path(source).resolve().as_uri() + "?mode=ro", uri=True)
        try:
            src.backup(self.conn)
        finally:
            src.close()
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.initialize()
