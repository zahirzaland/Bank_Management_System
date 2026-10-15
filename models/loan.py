from dataclasses import dataclass


@dataclass
class Loan:
    id: int
    loan_ref: str
    customer_id: int
    customer_name: str
    account_id: int
    account_number: str
    principal: int
    rate_basis_points: int
    term_months: int
    amount_due: int
    paid: int
    status: str
    notes: str
    applied_at: str

    @classmethod
    def from_row(cls, row) -> "Loan":
        return cls(
            row["id"], row["loan_ref"], row["customer_id"], row["customer_name"],
            row["account_id"], row["account_number"], row["principal_minor_units"],
            row["rate_basis_points"], row["term_months"], row["amount_due_minor"],
            row["paid_minor_units"], row["status"], row["notes"] or "", row["applied_at"],
        )

    @property
    def outstanding(self) -> int:
        return self.amount_due - self.paid
