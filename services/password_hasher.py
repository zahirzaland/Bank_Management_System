"""Password hashing (FR-02).

Preference order: Argon2 (argon2-cffi) -> bcrypt -> hashlib.scrypt.
All three are standard, salted, deliberately slow password-hashing functions;
no custom scheme is used. scrypt ships with Python so the app runs without
extra installs, but ``pip install argon2-cffi`` is recommended (see requirements.txt).
"""
import base64
import hashlib
import hmac
import os

try:  # optional dependencies
    from argon2 import PasswordHasher as _Argon2Hasher
    _argon2 = _Argon2Hasher()
except Exception:  # pragma: no cover - depends on environment
    _argon2 = None

try:
    import bcrypt as _bcrypt
except Exception:  # pragma: no cover
    _bcrypt = None

_N, _R, _P, _DKLEN = 2 ** 14, 8, 1, 32


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def active_scheme() -> str:
    return "argon2" if _argon2 else "bcrypt" if _bcrypt else "scrypt"


def hash_password(password: str) -> str:
    data = password.encode("utf-8")
    if _argon2:
        return _argon2.hash(password)
    if _bcrypt:
        return _bcrypt.hashpw(data, _bcrypt.gensalt()).decode("ascii")
    salt = os.urandom(16)
    digest = hashlib.scrypt(data, salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN)
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        data = password.encode("utf-8")
        if stored.startswith("$argon2"):
            return bool(_argon2) and _argon2.verify(stored, password)
        if stored.startswith("$2"):
            return bool(_bcrypt) and _bcrypt.checkpw(data, stored.encode("ascii"))
        if stored.startswith("scrypt$"):
            _, n, r, p, salt, expected = stored.split("$")
            digest = hashlib.scrypt(data, salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p),
                                    dklen=_DKLEN)
            return hmac.compare_digest(digest, base64.b64decode(expected))
    except Exception:
        return False
    return False
