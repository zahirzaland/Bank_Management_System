from dataclasses import dataclass
from typing import Optional


@dataclass
class Account:
    id: int
    account_number: str
    customer_id: int
    account_type: str
    balance: int  # integer minor units
    currency: str
    status: str
    opened_at: str
    closed_at: Optional[str]
    customer_name: str = ""
    customer_number: str = ""

    @classmethod
    def from_row(cls, row) -> "Account":
        keys = row.keys()
        return cls(row["id"], row["account_number"], row["customer_id"], row["account_type"],
                   row["balance_minor_units"], row["currency"], row["status"], row["opened_at"],
                   row["closed_at"],
                   row["customer_name"] if "customer_name" in keys else "",
                   row["customer_number"] if "customer_number" in keys else "")

    @property
    def is_active(self) -> bool:
        return self.status == "active"
