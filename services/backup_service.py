"""Database backup and restore (FR-19, NFR-07)."""
from pathlib import Path

import config
from utils import utc_now_compact
from .permissions import require


class BackupService:
    def __init__(self, db, audit):
        self.db, self.audit = db, audit

    @staticmethod
    def suggested_filename() -> str:
        return f"bank_backup_{utc_now_compact()}.db"

    def create_backup(self, actor, destination) -> Path:
        require(actor, "backup")
        path = self.db.backup_to(destination)
        with self.db.transaction():
            self.audit.add(actor.id, "backup_created", "database", None, path.name)
        return path

    def restore_backup(self, actor, source) -> None:
        """Replace all data with the backup. Callers must log the user out afterwards."""
        require(actor, "backup")
        self.db.restore_from(source)  # validates the file, takes a safety copy, then restores
        with self.db.transaction():
            # The restored data may not contain the acting user, so the entry is not attributed.
            self.audit.add(None, "backup_restored", "database", None, f"by {actor.username}: {Path(source).name}")
