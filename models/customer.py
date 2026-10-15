from dataclasses import dataclass
from typing import Optional


@dataclass
class Customer:
    id: int
    customer_number: str
    full_name: str
    phone: str
    email: Optional[str]
    address: Optional[str]
    status: str
    created_at: str
    updated_at: str
    kyc_status: str = "pending"
    kyc_notes: Optional[str] = None
    kyc_verified_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "Customer":
        keys = row.keys()
        return cls(row["id"], row["customer_number"], row["full_name"], row["phone"],
                   row["email"], row["address"], row["status"], row["created_at"], row["updated_at"],
                   row["kyc_status"] if "kyc_status" in keys else "pending",
                   row["kyc_notes"] if "kyc_notes" in keys else None,
                   row["kyc_verified_at"] if "kyc_verified_at" in keys else None)

    @property
    def is_active(self) -> bool:
        return self.status == "active"
