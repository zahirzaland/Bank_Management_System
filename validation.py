"""Input validation shared by services (FR-17)."""
import re

import config
from exceptions import ValidationError

_NAME_RE = re.compile(r"^[^\W\d_](?:[^\W\d_]|[ .'\-])+$")
_PHONE_RE = re.compile(r"^\+?[0-9][0-9 \-()]{6,19}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_USER_RE = re.compile(r"^[A-Za-z0-9_.\-]{3,32}$")


def clean_text(value, field: str, *, required: bool = False, max_len: int = 100, min_len: int = 0) -> str:
    text = " ".join(str(value or "").split())  # trims and collapses whitespace/newlines
    if not text:
        if required:
            raise ValidationError(f"{field} is required.")
        return ""
    if any(ord(c) < 32 or ord(c) == 127 for c in text):
        raise ValidationError(f"{field} contains invalid characters.")
    if len(text) < min_len:
        raise ValidationError(f"{field} must be at least {min_len} characters.")
    if len(text) > max_len:
        raise ValidationError(f"{field} must be at most {max_len} characters.")
    return text


def validate_customer(data: dict) -> dict:
    name = clean_text(data.get("full_name"), "Full name", required=True, max_len=100, min_len=2)
    if not _NAME_RE.match(name):
        raise ValidationError("Full name may contain only letters, spaces, apostrophes, hyphens and periods.")
    phone = clean_text(data.get("phone"), "Phone", required=True, max_len=20)
    if not _PHONE_RE.match(phone):
        raise ValidationError("Phone must be 7-20 characters: digits, spaces, hyphens, parentheses, optional leading +.")
    email = clean_text(data.get("email"), "Email", max_len=120)
    if email and not _EMAIL_RE.match(email):
        raise ValidationError("Email address is not in a valid format.")
    address = clean_text(data.get("address"), "Address", max_len=255)
    return {"full_name": name, "phone": phone, "email": email or None, "address": address or None}


def validate_username(username) -> str:
    name = str(username or "").strip()
    if not _USER_RE.match(name):
        raise ValidationError("Username must be 3-32 characters: letters, digits, '.', '_' or '-'.")
    return name


def validate_password(password) -> str:
    pw = str(password or "")
    if len(pw) < config.MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Password must be at least {config.MIN_PASSWORD_LENGTH} characters.")
    if len(pw.encode("utf-8")) > config.MAX_PASSWORD_BYTES:
        raise ValidationError(f"Password must be at most {config.MAX_PASSWORD_BYTES} bytes.")
    if not (any(c.isalpha() for c in pw) and any(c.isdigit() for c in pw)):
        raise ValidationError("Password must contain at least one letter and one digit.")
    return pw


def validate_role(role) -> str:
    if role not in config.ROLES:
        raise ValidationError("Role must be admin, teller or viewer.")
    return role
