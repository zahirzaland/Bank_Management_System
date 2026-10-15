from dataclasses import dataclass
from typing import Optional


@dataclass
class StaffUser:
    id: int
    username: str
    password_hash: str
    role: str
    is_active: bool
    created_at: str
    last_login_at: Optional[str]

    @classmethod
    def from_row(cls, row) -> "StaffUser":
        return cls(row["id"], row["username"], row["password_hash"], row["role"],
                   bool(row["is_active"]), row["created_at"], row["last_login_at"])

    def __repr__(self) -> str:  # never leak the hash in logs
        return f"StaffUser(id={self.id}, username={self.username!r}, role={self.role!r})"
