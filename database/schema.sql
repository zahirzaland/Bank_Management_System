-- Bank Management System schema (SQLite). Money is stored as integer minor units.
-- Timestamps are UTC text: YYYY-MM-DD HH:MM:SS

CREATE TABLE IF NOT EXISTS staff_users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK (role IN ('admin', 'teller', 'viewer')),
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at    TEXT    NOT NULL,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS customers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_number TEXT NOT NULL UNIQUE,
    full_name       TEXT NOT NULL CHECK (length(trim(full_name)) > 0),
    phone           TEXT NOT NULL,
    email           TEXT,
    address         TEXT,
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    kyc_status      TEXT NOT NULL DEFAULT 'pending' CHECK (kyc_status IN ('pending', 'verified', 'rejected')),
    kyc_notes       TEXT,
    kyc_verified_at TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number      TEXT    NOT NULL UNIQUE,
    customer_id         INTEGER NOT NULL REFERENCES customers (id),
    account_type        TEXT    NOT NULL,
    balance_minor_units INTEGER NOT NULL DEFAULT 0 CHECK (balance_minor_units >= 0),
    currency            TEXT    NOT NULL,
    status              TEXT    NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'frozen', 'closed')),
    opened_at           TEXT    NOT NULL,
    closed_at           TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_ref        TEXT    NOT NULL UNIQUE,
    transaction_type       TEXT    NOT NULL
        CHECK (transaction_type IN ('opening', 'deposit', 'withdrawal', 'transfer', 'reversal')),
    amount_minor_units     INTEGER NOT NULL CHECK (amount_minor_units > 0),
    currency               TEXT    NOT NULL,
    source_account_id      INTEGER REFERENCES accounts (id),
    destination_account_id INTEGER REFERENCES accounts (id),
    created_by             INTEGER NOT NULL REFERENCES staff_users (id),
    created_at             TEXT    NOT NULL,
    status                 TEXT    NOT NULL DEFAULT 'completed' CHECK (status IN ('completed', 'reversed')),
    note                   TEXT,
    reversed_of_id         INTEGER REFERENCES transactions (id),
    -- money always moves from a source, to a destination, or both - never between the same account
    CHECK (source_account_id IS NOT NULL OR destination_account_id IS NOT NULL),
    CHECK (source_account_id IS NULL OR destination_account_id IS NULL
           OR source_account_id <> destination_account_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_user_id INTEGER REFERENCES staff_users (id),
    action        TEXT NOT NULL,
    entity_type   TEXT,
    entity_id     TEXT,
    details       TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS loans (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_ref              TEXT NOT NULL UNIQUE,
    customer_id           INTEGER NOT NULL REFERENCES customers (id),
    account_id            INTEGER NOT NULL REFERENCES accounts (id),
    principal_minor_units INTEGER NOT NULL CHECK (principal_minor_units > 0),
    rate_basis_points     INTEGER NOT NULL CHECK (rate_basis_points >= 0 AND rate_basis_points <= 5000),
    term_months           INTEGER NOT NULL CHECK (term_months BETWEEN 1 AND 360),
    amount_due_minor      INTEGER NOT NULL CHECK (amount_due_minor >= principal_minor_units),
    paid_minor_units      INTEGER NOT NULL DEFAULT 0 CHECK (paid_minor_units >= 0),
    status                TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'active', 'paid')),
    notes                 TEXT,
    created_by            INTEGER NOT NULL REFERENCES staff_users (id),
    approved_by           INTEGER REFERENCES staff_users (id),
    applied_at            TEXT NOT NULL,
    disbursed_at          TEXT,
    CHECK (paid_minor_units <= amount_due_minor)
);

CREATE TABLE IF NOT EXISTS interest_applications (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id            INTEGER NOT NULL REFERENCES accounts (id),
    period                TEXT NOT NULL,
    rate_basis_points     INTEGER NOT NULL CHECK (rate_basis_points > 0),
    amount_minor_units    INTEGER NOT NULL CHECK (amount_minor_units > 0),
    transaction_id        INTEGER NOT NULL REFERENCES transactions (id),
    applied_at            TEXT NOT NULL,
    UNIQUE (account_id, period)
);

CREATE INDEX IF NOT EXISTS idx_customers_name       ON customers (full_name);
CREATE INDEX IF NOT EXISTS idx_accounts_customer    ON accounts (customer_id);
CREATE INDEX IF NOT EXISTS idx_loans_customer       ON loans (customer_id);
CREATE INDEX IF NOT EXISTS idx_interest_account     ON interest_applications (account_id, period);
CREATE INDEX IF NOT EXISTS idx_tx_created           ON transactions (created_at);
CREATE INDEX IF NOT EXISTS idx_tx_source            ON transactions (source_account_id);
CREATE INDEX IF NOT EXISTS idx_tx_destination       ON transactions (destination_account_id);
CREATE INDEX IF NOT EXISTS idx_audit_created        ON audit_logs (created_at);

-- Records linked to history are never physically deleted (FR-06, business rule 6).
CREATE TRIGGER IF NOT EXISTS trg_customers_no_delete BEFORE DELETE ON customers
BEGIN SELECT RAISE(ABORT, 'Customer records cannot be deleted; deactivate instead'); END;

CREATE TRIGGER IF NOT EXISTS trg_accounts_no_delete BEFORE DELETE ON accounts
BEGIN SELECT RAISE(ABORT, 'Account records cannot be deleted; close instead'); END;

CREATE TRIGGER IF NOT EXISTS trg_staff_no_delete BEFORE DELETE ON staff_users
BEGIN SELECT RAISE(ABORT, 'Staff records cannot be deleted; deactivate instead'); END;

CREATE TRIGGER IF NOT EXISTS trg_transactions_no_delete BEFORE DELETE ON transactions
BEGIN SELECT RAISE(ABORT, 'Transaction records cannot be deleted'); END;

-- Only the status may change (completed -> reversed); everything else is immutable.
CREATE TRIGGER IF NOT EXISTS trg_transactions_immutable BEFORE UPDATE ON transactions
WHEN NEW.transaction_ref IS NOT OLD.transaction_ref
  OR NEW.transaction_type IS NOT OLD.transaction_type
  OR NEW.amount_minor_units IS NOT OLD.amount_minor_units
  OR NEW.currency IS NOT OLD.currency
  OR NEW.source_account_id IS NOT OLD.source_account_id
  OR NEW.destination_account_id IS NOT OLD.destination_account_id
  OR NEW.created_by IS NOT OLD.created_by
  OR NEW.created_at IS NOT OLD.created_at
  OR NEW.note IS NOT OLD.note
  OR NEW.reversed_of_id IS NOT OLD.reversed_of_id
  OR (OLD.status = 'reversed' AND NEW.status <> 'reversed')
BEGIN SELECT RAISE(ABORT, 'Completed transactions cannot be edited'); END;

CREATE TRIGGER IF NOT EXISTS trg_audit_no_delete BEFORE DELETE ON audit_logs
BEGIN SELECT RAISE(ABORT, 'Audit records cannot be deleted'); END;

CREATE TRIGGER IF NOT EXISTS trg_audit_no_update BEFORE UPDATE ON audit_logs
BEGIN SELECT RAISE(ABORT, 'Audit records cannot be edited'); END;
