
"""Administrator tools: staff accounts, audit log, backup/restore."""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk

import config
from exceptions import BankError
from .widgets import BaseView, DataTable, add_field, set_message
from .i18n import tr, untr


class StaffView(BaseView):
    def __init__(self, parent, ctx):
        super().__init__(parent, ctx)
        self.configure(fg_color="#F7F8FC")

        self.title("Staff & Administration")

        self.nb = ctk.CTkTabview(
            self,
            fg_color="#F7F8FC",
            segmented_button_fg_color="#F7F8FC",
            segmented_button_selected_color="#4F83F1",
            segmented_button_unselected_color="#F7F8FC",
            segmented_button_selected_hover_color="#3C70DA",
            segmented_button_unselected_hover_color="#F7F8FC",
        )
        self.nb.pack(fill="both", expand=True, padx=6, pady=6)

        self.nb.add("Staff Accounts")
        self.nb.add("Audit Log")
        self.nb.add("Backup & Restore")

        for tab_name in ("Staff Accounts", "Audit Log", "Backup & Restore"):
            self.nb.tab(tab_name).configure(fg_color="#F7F8FC")

        self._users_tab(self.nb.tab("Staff Accounts"))
        self._audit_tab(self.nb.tab("Audit Log"))
        self._backup_tab(self.nb.tab("Backup & Restore"))

        self.refresh_users()
        self.refresh_audit()

    # ---- Staff accounts --------------------------------------------------


    def _users_tab(self, tab):
        """Responsive staff management layout."""

        self.u_name = tk.StringVar()
        self.u_pass = tk.StringVar()
        self.u_role = tk.StringVar(value=tr("teller"))

        # Main layout: table on the left, form on the right
        tab.grid_columnconfigure(0, weight=3, uniform="staff")
        tab.grid_columnconfigure(1, weight=2, uniform="staff")
        tab.grid_rowconfigure(0, weight=1)

        # =========================================================
        # LEFT PANEL: STAFF TABLE
        # =========================================================
        left = ctk.CTkFrame(
            tab,
            fg_color="#FFFFFF",
            corner_radius=12
        )
        left.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(12, 6),
            pady=12
        )

        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            left,
            text="Staff Accounts",
            font=ctk.CTkFont(size=19, weight="bold")
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=14,
            pady=(6, 4)
        )

        ctk.CTkLabel(
            left,
            text="Select a staff member to manage their account.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70")
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=14,
            pady=(60, 10)
        )

        self.u_table = DataTable(
            left,
            [
                ("Username", 130, "w"),
                ("Role", 85, "w"),
                ("Active", 65, "center"),
                ("Created (UTC)", 145, "w"),
                ("Last login (UTC)", 145, "w"),
            ],
            height=14,
        )

        self.u_table.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=10,
            pady=(0, 10)
        )

        # =========================================================
        # RIGHT PANEL: SCROLLABLE STAFF FORM AND ACTIONS
        # =========================================================
        right = ctk.CTkScrollableFrame(
            tab,
            fg_color="#FFFFFF",
            corner_radius=12,
            label_text="Staff Management",
            label_font=ctk.CTkFont(size=18, weight="bold")
        )
        right.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(6, 12),
            pady=12
        )

        right.grid_columnconfigure(0, weight=1)

        # Form card
        form = ctk.CTkFrame(
            right,
            fg_color="#FFFFFF",
            corner_radius=10
        )
        form.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=4,
            pady=(4, 10)
        )

        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            form,
            text="Create Staff Account",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            padx=14,
            pady=(14, 12)
        )

        add_field(
            form,
            1,
            "Username",
            self.u_name,
            width=24
        )

        add_field(
            form,
            2,
            "Password",
            self.u_pass,
            width=24,
            show="*"
        )

        ctk.CTkLabel(
            form,
            text="Staff Role"
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=10,
            pady=8
        )

        self.role_combo = ctk.CTkComboBox(
            form,
            variable=self.u_role,
            values=list(config.ROLES),
            state="readonly",
            height=36
        )
        self.role_combo.grid(
            row=3,
            column=1,
            sticky="ew",
            padx=10,
            pady=8
        )

        ctk.CTkLabel(
            form,
            text=(
                f"Password must contain at least "
                f"{config.MIN_PASSWORD_LENGTH} characters, "
                "including a letter and a digit."
            ),
            wraplength=280,
            justify="left",
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=11)
        ).grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="w",
            padx=12,
            pady=(8, 14)
        )

        # Actions card
        actions = ctk.CTkFrame(
            right,
            fg_color="#FFFFFF",
            corner_radius=10
        )
        actions.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=4,
            pady=(0, 10)
        )

        actions.grid_columnconfigure(
            (0, 1),
            weight=1
        )

        ctk.CTkLabel(
            actions,
            text="Account Actions",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            padx=12,
            pady=(14, 10)
        )

        ctk.CTkButton(
            actions,
            text="Create User",
            height=38,
            command=self.create_user
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(12, 5),
            pady=5
        )

        ctk.CTkButton(
            actions,
            text="Change Role",
            height=38,
            command=self.change_role
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(5, 12),
            pady=5
        )

        ctk.CTkButton(
            actions,
            text="Activate / Deactivate",
            height=38,
            fg_color="#B45309",
            hover_color="#92400E",
            command=self.toggle_active
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=12,
            pady=5
        )

        ctk.CTkButton(
            actions,
            text="Reset Password",
            height=38,
            fg_color="#475569",
            hover_color="#334155",
            command=self.reset_password
        ).grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=12,
            pady=(5, 14)
        )

        # Feedback card
        feedback = ctk.CTkFrame(
            right,
            fg_color="#FFFFFF",
            corner_radius=10
        )
        feedback.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=4,
            pady=(0, 10)
        )

        ctk.CTkLabel(
            feedback,
            text="Status",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(
            anchor="w",
            padx=12,
            pady=(12, 4)
        )

        self.u_msg = ctk.CTkLabel(
            feedback,
            text="Select a staff account to manage it.",
            wraplength=280,
            justify="left",
            anchor="w"
        )
        self.u_msg.pack(
            fill="x",
            padx=12,
            pady=(4, 12)
        )


    def refresh_users(self):
        try:
            users = self.ctx.auth.list_users(self.user)
        except Exception as exc:
            return self.fail(exc)

        self.u_table.set_rows(
            (
                u.id,
                (
                    u.username,
                    u.role,
                    "Yes" if u.is_active else "No",
                    u.created_at,
                    u.last_login_at or "-",
                ),
            )
            for u in users
        )

    def _selected_user_id(self):
        iid = self.u_table.selected()

        if iid is None:
            set_message(
                self.u_msg,
                "Select a staff user in the table first.",
                ok=False,
            )
            return None

        try:
            return int(iid)
        except (TypeError, ValueError):
            set_message(
                self.u_msg,
                "The selected user ID is invalid.",
                ok=False,
            )
            return None

    def _do(self, action, success_text):
        try:
            action()
        except BankError as exc:
            return set_message(self.u_msg, str(exc), ok=False)
        except Exception as exc:
            return self.fail(exc)

        self.refresh_users()
        self.refresh_audit()

        set_message(
            self.u_msg,
            success_text,
            ok=True,
        )

    def create_user(self):
        def action():
            self.ctx.auth.create_user(
                self.user,
                self.u_name.get().strip(),
                self.u_pass.get(),
                untr(self.u_role.get()),
            )
            self.u_name.set("")
            self.u_pass.set("")

        self._do(action, "Staff user created.")

    def change_role(self):
        uid = self._selected_user_id()

        if uid is not None:
            self._do(
                lambda: self.ctx.auth.change_role(
                    self.user,
                    uid,
                    untr(self.u_role.get()),
                ),
                "Role updated.",
            )

    def toggle_active(self):
        uid = self._selected_user_id()

        if uid is None:
            return

        try:
            users = self.ctx.auth.list_users(self.user)
        except Exception as exc:
            return self.fail(exc)

        target = next(
            (u for u in users if u.id == uid),
            None,
        )

        if target is None:
            return set_message(
                self.u_msg,
                "Selected staff user was not found.",
                ok=False,
            )

        self._do(
            lambda: self.ctx.auth.set_active(
                self.user,
                uid,
                not target.is_active,
            ),
            (
                "Staff user deactivated."
                if target.is_active
                else "Staff user activated."
            ),
        )

    def reset_password(self):
        uid = self._selected_user_id()

        if uid is None:
            return

        new_password = simpledialog.askstring(
            "Reset password",
            "New password for the selected user:",
            show="*",
            parent=self,
        )

        if new_password is not None:
            self._do(
                lambda: self.ctx.auth.reset_password(
                    self.user,
                    uid,
                    new_password,
                ),
                "Password reset.",
            )

    # ---- Audit log -------------------------------------------------------

    def _audit_tab(self, tab):
        self.a_filter = tk.StringVar()

        bar = ctk.CTkFrame(
            tab,
            fg_color="transparent",
        )
        bar.pack(
            fill="x",
            padx=8,
            pady=(8, 6),
        )

        ctk.CTkLabel(
            bar,
            text="Filter (action, user, details)",
        ).pack(side="left", padx=(0, 8))

        entry = ctk.CTkEntry(
            bar,
            textvariable=self.a_filter,
            width=250,
            placeholder_text="Search audit log...",
        )
        entry.pack(side="left", padx=4)
        entry.bind(
            "<Return>",
            lambda _event: self.refresh_audit(),
        )

        ctk.CTkButton(
            bar,
            text="Refresh",
            command=self.refresh_audit,
            width=100,
        ).pack(side="left", padx=6)

        self.a_table = DataTable(
            tab,
            [
                ("ID", 50, "e"),
                ("Time (UTC)", 130, "w"),
                ("User", 90, "w"),
                ("Action", 160, "w"),
                ("Entity", 80, "w"),
                ("Entity ID", 70, "w"),
                ("Details", 380, "w"),
            ],
            height=16,
        )
        self.a_table.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=(0, 8),
        )

    def refresh_audit(self):
        try:
            entries = self.ctx.reports.audit_entries(
                self.user,
                self.a_filter.get(),
            )
        except Exception as exc:
            return self.fail(exc)

        self.a_table.set_rows(
            (
                e["id"],
                (
                    e["id"],
                    e["created_at"],
                    e["username"],
                    e["action"],
                    e["entity_type"],
                    e["entity_id"],
                    e["details"],
                ),
            )
            for e in entries
        )

    # ---- Backup and restore ---------------------------------------------

    def _backup_tab(self, tab):
        description = (
            "Backup creates a consistent copy of the whole database "
            "using SQLite's online backup facility; it is safe while "
            "the application is open.\n\n"
            "Restore replaces ALL current data with the contents of "
            "a backup file. A safety copy of the current database is "
            "saved first (data/backups/pre_restore_*.db). After a "
            "restore you are signed out, because staff accounts come "
            "from the restored data."
        )

        ctk.CTkLabel(
            tab,
            text=description,
            wraplength=720,
            justify="left",
            anchor="w",
        ).pack(
            anchor="w",
            fill="x",
            padx=12,
            pady=(14, 8),
        )

        buttons = ctk.CTkFrame(
            tab,
            fg_color="transparent",
        )
        buttons.pack(
            anchor="w",
            padx=8,
            pady=12,
        )

        ctk.CTkButton(
            buttons,
            text="Create backup...",
            command=self.create_backup,
            width=160,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            buttons,
            text="Restore from backup...",
            command=self.restore_backup,
            width=190,
        ).pack(side="left")

        self.b_msg = ctk.CTkLabel(
            tab,
            text="",
            wraplength=720,
            justify="left",
            anchor="w",
        )
        self.b_msg.pack(
            anchor="w",
            fill="x",
            padx=12,
            pady=(4, 8),
        )

    def create_backup(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save backup",
            defaultextension=".db",
            initialfile=self.ctx.backup.suggested_filename(),
            filetypes=[("SQLite backup", "*.db")],
        )

        if not path:
            return

        try:
            saved = self.ctx.backup.create_backup(
                self.user,
                path,
            )
        except BankError as exc:
            return set_message(self.b_msg, str(exc), ok=False)
        except Exception as exc:
            return self.fail(exc)

        set_message(
            self.b_msg,
            f"Backup saved to {saved}",
            ok=True,
        )
        self.refresh_audit()

    def restore_backup(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Choose a backup to restore",
            filetypes=[
                ("SQLite backup", "*.db"),
                ("All files", "*.*"),
            ],
        )

        if not path:
            return

        confirmed = messagebox.askyesno(
            "Restore backup",
            (
                "This replaces ALL current data with the selected "
                "backup.\n\nContinue?"
            ),
            icon="warning",
            parent=self,
        )

        if not confirmed:
            return

        try:
            self.ctx.backup.restore_backup(
                self.user,
                path,
            )
        except BankError as exc:
            return set_message(self.b_msg, str(exc), ok=False)
        except Exception as exc:
            return self.fail(exc)

        messagebox.showinfo(
            "Restore complete",
            "The backup was restored. Please sign in again.",
            parent=self,
        )

        if self.ctx.request_logout:
            self.ctx.request_logout()
