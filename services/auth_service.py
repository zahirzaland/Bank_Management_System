"""Authentication and staff management (FR-01, FR-02, FR-03, business rule 7)."""
import time
from typing import List

import config
from exceptions import AuthenticationError, DuplicateError, NotFoundError, ValidationError
from models import StaffUser
from validation import validate_password, validate_role, validate_username
from . import password_hasher
from .permissions import require

_dummy_hash = None


def _dummy() -> str:
    """Hash checked for unknown usernames so response time does not reveal valid accounts."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = password_hasher.hash_password("not-a-real-password-1")
    return _dummy_hash


class AuthService:
    def __init__(self, db, staff, audit):
        self.db, self.staff, self.audit = db, staff, audit
        self._failures = {}  # username(lower) -> (consecutive failures, locked_until)

    # ---- first run -------------------------------------------------------
    def needs_bootstrap(self) -> bool:
        return self.staff.count() == 0

    def bootstrap_admin(self, username: str, password: str) -> StaffUser:
        """Create the very first administrator. Allowed only while no staff exist."""
        username, password = validate_username(username), validate_password(password)
        with self.db.transaction():
            if not self.needs_bootstrap():
                raise ValidationError("Setup has already been completed.")
            user = self.staff.create(username, password_hasher.hash_password(password), "admin")
            self.audit.add(user.id, "staff_created", "staff_user", user.id, f"first administrator '{username}'")
        return user

    # ---- login / logout --------------------------------------------------
    def login(self, username: str, password: str) -> StaffUser:
        username = (username or "").strip()
        if not username or not password:
            raise AuthenticationError("Enter both username and password.")
        key = username.lower()
        count, locked_until = self._failures.get(key, (0, 0.0))
        remaining = int(locked_until - time.monotonic())
        if remaining > 0:
            raise AuthenticationError(f"Too many failed attempts. Try again in {remaining} seconds.")

        user = self.staff.get_by_username(username)
        verified = password_hasher.verify_password(password, user.password_hash if user else _dummy())
        if not (user and verified and user.is_active):
            count += 1
            lock = time.monotonic() + config.LOGIN_LOCK_SECONDS if count >= config.MAX_LOGIN_ATTEMPTS else 0.0
            self._failures[key] = (0 if lock else count, lock)
            with self.db.transaction():
                self.audit.add(user.id if user else None, "login_failed", "staff_user",
                               user.id if user else None, f"username={username[:50]}")
            raise AuthenticationError("Invalid username or password.")

        self._failures.pop(key, None)
        with self.db.transaction():
            self.staff.touch_login(user.id)
            self.audit.add(user.id, "login_success", "staff_user", user.id)
        return self.staff.get(user.id)

    def logout(self, user: StaffUser) -> None:
        with self.db.transaction():
            self.audit.add(user.id, "logout", "staff_user", user.id)

    # ---- staff management (administrators only) --------------------------
    def list_users(self, actor: StaffUser) -> List[StaffUser]:
        require(actor, "manage_staff")
        return self.staff.list_all()

    def _target(self, user_id: int) -> StaffUser:
        target = self.staff.get(user_id)
        if not target:
            raise NotFoundError("Staff user not found.")
        return target

    def _guard_last_admin(self, target: StaffUser) -> None:
        if target.role == "admin" and target.is_active and self.staff.count_active_admins() <= 1:
            raise ValidationError("At least one active administrator must remain.")

    def create_user(self, actor: StaffUser, username: str, password: str, role: str) -> StaffUser:
        require(actor, "manage_staff")
        username, password, role = validate_username(username), validate_password(password), validate_role(role)
        with self.db.transaction():
            if self.staff.get_by_username(username):
                raise DuplicateError("That username is already in use.")
            user = self.staff.create(username, password_hasher.hash_password(password), role)
            self.audit.add(actor.id, "staff_created", "staff_user", user.id, f"username={username}, role={role}")
        return user

    def change_role(self, actor: StaffUser, user_id: int, role: str) -> None:
        require(actor, "manage_staff")
        role = validate_role(role)
        with self.db.transaction():
            target = self._target(user_id)
            if target.id == actor.id:
                raise ValidationError("You cannot change your own role.")
            if role != "admin":
                self._guard_last_admin(target)
            self.staff.set_role(user_id, role)
            self.audit.add(actor.id, "staff_role_changed", "staff_user", user_id,
                           f"{target.username}: {target.role} -> {role}")

    def set_active(self, actor: StaffUser, user_id: int, active: bool) -> None:
        require(actor, "manage_staff")
        with self.db.transaction():
            target = self._target(user_id)
            if not active:
                if target.id == actor.id:
                    raise ValidationError("You cannot deactivate your own account.")
                self._guard_last_admin(target)
            self.staff.set_active(user_id, active)
            self.audit.add(actor.id, "staff_activated" if active else "staff_deactivated",
                           "staff_user", user_id, target.username)

    def reset_password(self, actor: StaffUser, user_id: int, new_password: str) -> None:
        require(actor, "manage_staff")
        new_password = validate_password(new_password)
        with self.db.transaction():
            target = self._target(user_id)
            self.staff.set_password_hash(user_id, password_hasher.hash_password(new_password))
            self.audit.add(actor.id, "staff_password_reset", "staff_user", user_id, target.username)

    def change_own_password(self, user: StaffUser, current: str, new: str) -> None:
        new = validate_password(new)
        fresh = self._target(user.id)
        if not password_hasher.verify_password(current or "", fresh.password_hash):
            raise AuthenticationError("Current password is incorrect.")
        with self.db.transaction():
            self.staff.set_password_hash(user.id, password_hasher.hash_password(new))
            self.audit.add(user.id, "password_changed", "staff_user", user.id)
