from dataclasses import dataclass
from typing import Optional


@dataclass
class Transaction:
    id: int
    ref: str
    transaction_type: str
    amount: int  # integer minor units
    currency: str
    source_account_id: Optional[int]
    destination_account_id: Optional[int]
    created_by: int
    created_at: str
    status: str
    note: Optional[str]
    reversed_of_id: Optional[int]
    source_account_number: Optional[str]
    destination_account_number: Optional[str]
    created_by_username: str

    @classmethod
    def from_row(cls, row) -> "Transaction":
        return cls(row["id"], row["transaction_ref"], row["transaction_type"], row["amount_minor_units"],
                   row["currency"], row["source_account_id"], row["destination_account_id"],
                   row["created_by"], row["created_at"], row["status"], row["note"],
                   row["reversed_of_id"], row["source_account_number"],
                   row["destination_account_number"], row["created_by_username"])
