"""Small runtime localization layer for the desktop interface.

Persisted domain values stay in English for compatibility with the database;
only labels presented to people are translated.
"""
import re

LANGUAGES = {"en": "English", "ps": "پښتو"}

_PS = {
    "Bank Management System": "د بانکونو د چارو سمبالښت",
    "Educational simulation - Designed just for improving development": "د زده کړې او تمرین لپاره جوړ شوی",
    "Educational Simulation": "ښوونیزه بېلګه",
    "BANKING SYSTEM": "د بانکدارۍ سیستم", "WORKSPACE": "کاري برخه", "Overview": "لنډیز",
    "Customers": "پېرودونکي", "Accounts": "حسابونه", "Transactions": "کړنې",
    "Loans": "پورونه", "Interest": "ګټه", "Reports": "راپورونه", "Staff": "کارکوونکي",
    "Log Out": "وتل", "Change Password": "پټ نوم بدلول", "Welcome, ": "ښه راغلاست، ",
    "Role: ": "دنده: ", "admin": "اداري مسؤول", "teller": "د بانک کارکوونکی", "viewer": "یوازې لیدل",
    "Bank Overview": "د بانک لنډیز", "Real-time summary from your banking records": "ستاسو د بانک د چارو تازه لنډیز",
    "Quick Access": "چټک لاسرسی", "Open a module to manage its records.": "د چارو د سمبالولو لپاره یوه برخه پرانیزئ.",
    "Total Balance": "ټوله شتمني", "Registered customers": "ثبت شوي پېرودونکي",
    "Accounts in the system": "ټول حسابونه", "Recorded transactions": "ثبت شوې کړنې",
    "Current account balances": "د حسابونو اوسنۍ شتمني", "Transaction Counts": "د کړنو شمېر",
    "Transaction Amounts": "د کړنو پیسې", "Accounts of Selected Customer": "د ټاکل شوي پېرودونکي حسابونه",
    "Customer Details": "د پېرودونکي معلومات", "Customer management (FR-04, FR-05, FR-06, UC-02).": "د پېرودونکو ثبت او سمبالښت",
    "Full name *": "بشپړ نوم *", "Phone *": "د اړیکې شمېره *", "Email": "برېښنالیک",
    "Address": "پته", "Search customers": "پېرودونکي ولټوئ", "Find customer (ID or name)": "د پېژندپاڼې شمېره یا نوم ولیکئ",
    "Find": "لټون", "Clear": "پاکول", "Update": "سمون", "Deactivate": "غیرفعالول", "Reactivate": "بیا فعالول",
    "Customer ID": "د پېرودونکي شمېره", "Customer": "پېرودونکی", "Name": "نوم", "Phone": "د اړیکې شمېره",
    "KYC status": "د پېژندنې تایید", "KYC verification": "د پېرودونکي د پېژندنې تایید",
    "KYC update": "د پېژندنې حالت بدلول", "Review status": "د ارزونې پایله", "Review notes": "د ارزونې یادښتونه",
    "Save KYC Status": "د پېژندنې حالت خوندي کول", "pending": "تر ارزونې لاندې", "verified": "تایید شوی", "rejected": "رد شوی",
    "Accounts": "حسابونه", "Account Actions": "د حساب چارې", "Open a New Account": "نوی حساب پرانیستل",
    "Open Account": "حساب پرانیستل", "Account type": "د حساب ډول", "Opening balance": "لومړنۍ شتمني",
    "Account No.": "د حساب شمېره", "Account number": "د حساب شمېره", "Balance": "شتمني",
    "Status": "حالت", "Opened (UTC)": "د پرانیستلو نېټه", "Close Account": "حساب تړل",
    "Freeze": "لنډمهاله بندول", "Unfreeze": "بیا پرانیستل", "active": "فعال", "frozen": "لنډمهاله بند",
    "closed": "تړل شوی", "Deposit / Withdraw": "پیسې اچول یا ایستل", "Deposit": "پیسې اچول",
    "Withdraw": "پیسې ایستل", "Transfer": "پیسې لېږدول", "Amount": "اندازه", "Note (optional)": "یادښت (اختیاري)",
    "From account": "له حساب څخه", "To account": "دې حساب ته", "Submit Transaction": "کړنه ثبتول",
    "History & Search": "د کړنو مخینه او لټون", "Search accounts": "حسابونه ولټوئ",
    "ID, name or account no.": "شمېره، نوم یا د حساب شمېره", "Txn ID / ref": "د کړنې شمېره",
    "Date/Time (UTC)": "نېټه او وخت", "Type": "ډول", "Reference": "د پېژندنې شمېره",
    "Created (UTC)": "د ثبت نېټه", "From": "له", "To": "ته", "Staff": "کارکوونکی",
    "Details": "جزیات", "Action": "کړنه", "Entity": "اړوند توکی", "Entity ID": "د توکي شمېره",
    "Deposit account": "حساب ته پیسې اچول", "Principal": "اصلي پور", "APR (%)": "کلنۍ ګټه (سلنه)",
    "Months": "میاشتې", "Term (months)": "د پور موده (میاشتې)", "Apply for Loan": "د پور غوښتنه",
    "Approve": "منل", "Reject": "ردول", "Disburse": "د پور پیسې ورکول", "Record Repayment": "د پور قسط ثبتول",
    "Payment amount": "د ورکړې اندازه", "Amount Due": "ټوله ورکړه", "Loan Ref": "د پور شمېره",
    "Loan applications, approval, disbursement and repayments.": "د پور غوښتنه، منل، ورکړه او بېرته اخیستل.",
    "Monthly Interest": "میاشتنۍ ګټه", "Period (YYYY-MM)": "میاشت (کال-میاشت)", "Preview": "مخکتنه",
    "English": "انګلیسي", "پښتو": "پښتو", "Language": "ژبه", "All transactions": "ټولې کړنې",
    "Deposits": "پیسې اچول", "Withdrawals": "پیسې ایستل", "Transfers": "پیسې لېږدول",
    "Reversals": "بېرته ګرځول", "Accounts opened": "پرانیستل شوي حسابونه", "Account Type": "د حساب ډول",
    "Current Balance": "اوسنۍ شتمني", "Account": "حساب", "OK": "سم", "MISMATCH": "ناسم",
    "Transaction type": "د کړنې ډول", "CSV files": "CSV دوتنې", "PDF files": "PDF دوتنې",
    "Your password was changed successfully.": "ستاسو پټ نوم بدل شو.",
    "No active customer matches that search.": "د لټون له مخې فعال پېرودونکی ونه موندل شو.",
    "Select a staff account to manage it.": "د سمبالولو لپاره د کارکوونکي حساب وټاکئ.",
    "Select a staff member to manage their account.": "د حساب د سمبالولو لپاره کارکوونکی وټاکئ.",
    "Select a staff user in the table first.": "لومړی له لست څخه کارکوونکی وټاکئ.",
    "Select a transaction to reverse.": "د بېرته ګرځولو لپاره کړنه وټاکئ.",
    "A reversal reason is required.": "د بېرته ګرځولو لامل ولیکئ.", "Amount must be greater than zero.": "اندازه باید له صفره زیاته وي.",
    "Source and destination accounts must be different.": "د پیسو د لېږلو او ترلاسه کولو حسابونه باید جلا وي.",
    "Transaction": "راکړه ورکړه",
    "Transactions": "راکړې ورکړې",
    "Recorded transactions": "ثبت شوې راکړې ورکړې",
    "Transaction Counts": "د راکړې ورکړې شمېر",
    "Transaction Amounts": "د راکړې ورکړې پیسې",
    "Transaction type": "د راکړې ورکړې ډول",
    "Transaction Summary": "د راکړې ورکړې لنډیز",
    "Transaction Details": "د راکړې ورکړې جزیات",
    "Submit Transaction": "راکړه ورکړه ثبتول",
    "History & Search": "د راکړې ورکړې مخینه او لټون",
    "Reverse Selected...": "ټاکل شوې راکړه ورکړه بېرته ګرځول...",
    "Txn ID / ref": "د راکړې ورکړې شمېره",
    "Customer": "مشتري",
    "Customers": "مشتریان",
    "Registered customers": "ثبت شوي مشتریان",
    "Search customers": "مشتریان ولټوئ",
    "Accounts of Selected Customer": "د ټاکل شوي مشتری حسابونه",
    "Customer ID": "د مشتری پېژندشمېره",
    "Account Actions": "د حساب چارې",
    "Deposit / Withdraw": "حساب ته پیسې اچول یا ترې ایستل",
    "Total Balance": "د ټولو حسابونو پاتې پیسې",
    "Current account balances": "د حسابونو اوسنۍ پاتې پیسې",
    "Recorded transactions": "ثبت شوې راکړې ورکړې",
    "Opening balance": "د حساب د پیل پیسې",
    "Submit": "ثبتول",
    "Update": "معلومات سمول",
    "Clear": "تشول",
    "Reset": "بیا ټاکل",
    "Look up": "حساب پیدا کول",
    "Find": "پیدا کول",
    "Action": "ترسره شوی کار",
    "Entity": "اړوند ریکارډ",
    "Entity ID": "د ریکارډ شمېره",
    "Details": "نور معلومات",
    "From": "له حسابه",
    "To": "حساب ته",
    "Staff": "کارکوونکی",
    "Note (optional)": "یادښت (اړین نه دی)",
    "All transactions": "ټولې راکړې ورکړې",
    "Both accounts must be active.": "د پیسو لېږلو لپاره باید دواړه حسابونه فعال وي.",
    "This account is not available for transactions.": "په دې حساب کې راکړه ورکړه نه شي کېدای.",
    "Select a transaction to reverse.": "لومړی هغه راکړه ورکړه وټاکئ چې بېرته یې ګرځوئ.",
    "Your role may view and search transactions but cannot create them.": "تاسو راکړې ورکړې لیدل او لټولای شئ، خو نوې راکړه ورکړه نه شئ ثبتولای.",
    "Both accounts must be active.": "دواړه حسابونه باید فعال وي.", "This account is not available for transactions.": "په دې حساب کې کړنې نشي ترسره کېدای.",
    "Export report": "راپور خوندي کول", "Export report as PDF": "راپور د PDF په بڼه خوندي کول",
    "Choose a backup to restore": "د بېرته راوستلو لپاره خوندي کاپي وټاکئ",
    "Staff user created.": "د کارکوونکي حساب جوړ شو.", "Staff user activated.": "د کارکوونکي حساب فعال شو.",
    "Staff user deactivated.": "د کارکوونکي حساب غیرفعال شو.", "Role updated.": "دنده بدله شوه.",
    "Save New": "نوی ثبتول", "Cancel": "بېرته", "Save": "خوندي کول",
    "Save backup": "خوندي کاپي جوړول", "Staff Role": "د کارکوونکي دنده", "Update KYC": "د پېژندنې حالت بدلول",
    "YYYY-MM-DD": "کال-میاشت-ورځ", "Backup saved to ": "خوندي کاپي دلته خوندي شوه: ",
    "Restore complete": "بېرته راوستل بشپړ شول", "Choose a backup to restore": "د بېرته راوستلو لپاره خوندي کاپي وټاکئ",
    "Account no., customer ID or name": "د حساب شمېره، د پېرودونکي شمېره یا نوم",
    "Enter customer ID or name": "د پېرودونکي شمېره یا نوم ولیکئ", "ID, name or account no.": "شمېره، نوم یا د حساب شمېره",
    "Search accounts": "حسابونه ولټوئ", "Open a New Account": "نوی حساب پرانیستل",
    "Find customer (ID or name)": "د پېژندپاڼې شمېره یا نوم ولیکئ", "Accounts of Selected Customer": "د ټاکل شوي پېرودونکي حسابونه",
    "Select a customer from the list to view their accounts.": "د حسابونو د لیدلو لپاره له لست څخه پېرودونکی وټاکئ.",
    "Withdrawal": "پیسې ایستل", "Transaction type": "د کړنې ډول", "Submit Transaction": "کړنه ثبتول",
    "Reverse Selected...": "ټاکل شوې کړنه بېرته ګرځول...", "Look up": "لټون", "Reset": "بیا ټاکل",
    "Bank Overview": "د بانک لنډیز", "Real-time summary from your banking records": "ستاسو د بانک د چارو تازه لنډیز",
    "Select a customer and account and enter valid amount, APR, and term.": "پېرودونکی او حساب وټاکئ، او د پیسو اندازه، کلنۍ ګټه او موده سمه ولیکئ.",
    "Customer ": "پېرودونکی ", " created.": " ثبت شو.", " updated.": " تازه شو.",
    "KYC status updated.": "د پېژندنې حالت بدل شو.", "Loan record updated.": "د پور معلومات تازه شول.",
    "The backup was restored. Please sign in again.": "خوندي شوي معلومات بېرته راوګرځېدل. بیا ننوځئ.",
    "Account opening and status management (FR-07, FR-08, FR-12, UC-03).": "د حساب پرانیستل او حالت سمبالول.",
    "Deposits, withdrawals, transfers, history and search (FR-09 FR-14, UC-04 UC-06).": "پیسې اچول، ایستل، لېږل، مخینه او لټون.",
    "Illustrative fixed-rate loans: total interest is calculated once from APR and term.": "د پور ټولیزه ګټه د کلنۍ کچې او مودې له مخې اټکلېږي.",
    "Illustrative monthly simple interest: credited once per account and month.": "ساده میاشتنۍ ګټه هر حساب ته په میاشت کې یو ځل اچول کېږي.",
    "Record the review outcome. Do not enter real identity document numbers.": "د ارزونې پایله ولیکئ. د پېژندپاڼې رښتینې شمېره مه لیکئ.",
    "Your role may view and search transactions but cannot create them.": "ستاسو دنده د کړنو د لیدلو او لټولو اجازه لري، خو نوې کړنه نشي ثبتولی.",
    "Reports permission is required to view these statistics.": "د دې شمېرو د لیدلو لپاره د راپور اجازه اړینه ده.",
    "Leave a date empty for no limit. The Ledger Consistency Check and the current balances in Account Summary ignore dates. All times are UTC.": "د نېټې ځای تش پرېږدئ چې د وخت محدودیت ونلري. د حسابونو د سمون کتنه او اوسنۍ شتمني نېټې نه کاروي.",
    "An unexpected error occurred and the action was not completed. Details were written to the application log.": "ناڅاپي ستونزه رامنځته شوه او غوښتنه بشپړه نشوه. د ستونزې جزیات د پروګرام په ثبت کې خوندي شول.",
    "Choose a password different from your current one.": "له اوسني پټ نوم څخه بل پټ نوم وټاکئ.",
    "Password must contain at least one letter and one digit.": "پټ نوم باید لږ تر لږه یو توری او یوه شمېره ولري.",
    "Password must contain at least ": "پټ نوم باید لږ تر لږه ",
    "Username must be 3-32 characters: letters, digits, '.', '_' or '-'.": "د ننوتلو نوم باید له ۳ تر ۳۲ تورو او شمېرو وي؛ ټکي، نښلونکی کرښه او لاندینۍ کرښه هم منل کېږي.",
    "Role must be admin, teller or viewer.": "د کارن لپاره اداري مسؤول، د بانک کارکوونکی یا یوازې لیدل وټاکئ.",
    "Email address is not in a valid format.": "د برېښنالیک بڼه سمه نه ده.",
    "Full name may contain only letters, spaces, apostrophes, hyphens and periods.": "په بشپړ نوم کې یوازې توري، تش ځایونه او د نوم نښې کارولای شئ.",
    "Phone must be 7-20 characters: digits, spaces, hyphens, parentheses, optional leading +.": "د اړیکې شمېره باید له ۷ تر ۲۰ تورو وي؛ شمېرې، تش ځای، قوس او نښلونکی کرښه منل کېږي.",
    "Authentication failed.": "د ننوتلو نوم یا پټ نوم سم نه دی.",
    "Invalid username or password.": "د ننوتلو نوم یا پټ نوم سم نه دی.",
    "This account is temporarily locked. Try again later.": "دا حساب لنډمهاله تړل شوی. وروسته بیا هڅه وکړئ.",
    "The new passwords do not match.": "نوي پټ نومونه سره یو شان نه دي.",
    "The selected user ID is invalid.": "د ټاکل شوي کارن شمېره ناسمه ده.",
    "Selected staff user was not found.": "ټاکل شوی کارکوونکی ونه موندل شو.",
    "No staff accounts exist yet. Create the first administrator account.": "تر اوسه د کارکوونکو حساب نشته. لومړی اداري حساب جوړ کړئ.",
    "The backup was restored. Please sign in again.": "خوندي شوي معلومات بېرته راوګرځېدل. بیا ننوځئ.",
    "A closed account cannot be reopened.": "تړل شوی حساب بېرته نه پرانیستل کېږي.",
    "An account cannot be opened until customer verification is complete.": "تر تایید مخکې د پېرودونکي لپاره حساب نه پرانیستل کېږي.",
    "Customer verification is required before applying for a loan.": "د پور غوښتلو لپاره د پېرودونکي تایید اړین دی.",
    "The selected customer was not found.": "ټاکل شوی پېرودونکی ونه موندل شو.",
    "Enter a valid account number.": "د حساب سمه شمېره ولیکئ.",
    "Enter valid source and destination account numbers.": "د لېږلو او ترلاسه کولو حسابونو سمې شمېرې ولیکئ.",
    "Find and select a customer first.": "لومړی پېرودونکی ولټوئ او ویې ټاکئ.",
    "The selected account was not found.": "ټاکل شوی حساب ونه موندل شو.",
    "The selected user was not found.": "ټاکل شوی کارن ونه موندل شو.",
    "Select a customer and account and enter valid amount, APR, and term.": "پېرودونکی او حساب وټاکئ، او د پیسو اندازه، کلنۍ ګټه او موده سمه ولیکئ.",
    "No": "نه", "All": "ټول", "Opening": "پرانیستل", "opening": "پرانیستل",
    "deposit": "پیسې اچول", "withdrawal": "پیسې ایستل", "transfer": "لېږد", "reversal": "بېرته ګرځول",
    "Savings": "سپما", "Checking": "د ورځنیو چارو", "Fixed Deposit": "ثابت سپما",
    "Transaction Summary": "د کړنو لنډیز", "Transaction Details": "د کړنو جزیات",
    "Export complete": "صادرول بشپړ شول", "Restore complete": "بېرته راوستل بشپړ شول",
    "Apply Interest": "ګټه حساب ته اچول", "Annual Rate": "کلنۍ ګټه", "Interest Credit": "حساب ته اچول شوې ګټه",
    "Applied (UTC)": "د پلي کېدو نېټه", "Preview interest before applying.": "تر پلي کولو مخکې د ګټې اندازه وګورئ.",
    "Report": "راپور", "Generate": "راپور جوړول", "From (YYYY-MM-DD)": "له نېټې (کال-میاشت-ورځ)",
    "To (YYYY-MM-DD)": "تر نېټې (کال-میاشت-ورځ)", "Export CSV...": "CSV بڼه کې خوندي کول...",
    "Export PDF...": "PDF بڼه کې خوندي کول...", "Transaction Summary": "د کړنو لنډیز",
    "Transaction Details": "د کړنو جزیات", "Account Summary": "د حسابونو لنډیز",
    "Ledger Consistency Check": "د حسابونو د سمون کتنه", "Count": "شمېر", "Total Balance": "ټوله شتمني",
    "Stored Balance": "ثبت شوې شتمني", "Ledger Balance": "د کړنو له مخې شتمني", "Result": "پایله",
    "From (YYYY-MM-DD)": "له نېټې (کال-میاشت-ورځ)", "To (YYYY-MM-DD)": "تر نېټې (کال-میاشت-ورځ)",
    "Staff & Administration": "کارکوونکي او اداره", "Staff Management": "د کارکوونکو سمبالښت",
    "Staff Accounts": "د کارکوونکو حسابونه", "Create Staff Account": "د کارکوونکي حساب جوړول",
    "Create Administrator": "اداري حساب جوړول", "Create User": "کارن جوړول", "Username": "د ننوتلو نوم",
    "Password": "پټ نوم", "Role": "دنده", "Change Role": "دنده بدلول", "Activate / Deactivate": "فعالول یا بندول",
    "Reset Password": "پټ نوم بیا ټاکل", "Audit Log": "د چارو ثبت", "Backup & Restore": "د معلوماتو خوندي کول او بېرته راوستل",
    "Create backup...": "د معلوماتو خوندي کاپي جوړول...", "Restore from backup...": "له خوندي کاپي معلومات راوستل...",
    "Filter (action, user, details)": "د کړنې، کارن یا جزیاتو له مخې لټون", "Search audit log...": "د چارو ثبت ولټوئ...",
    "Sign In": "ننوتل", "Staff Sign In": "د کارکوونکي ننوتل", "First-time setup": "لومړنی جوړښت",
    "No staff accounts exist yet. Create the first administrator account.": "تر اوسه اداري حساب نشته. لومړی اداري حساب جوړ کړئ.",
    "Current Password": "اوسنی پټ نوم", "New Password": "نوی پټ نوم", "Confirm New Password": "نوی پټ نوم بیا ولیکئ",
    "Show passwords": "پټ نومونه ښکاره کول", "Cancel": "بېرته", "Setup": "چمتو کول", "Optional": "اختیاري",
    "Success": "بریالی شو", "Error": "ستونزه", "Session expired": "ستاسو ناسته پای ته ورسېده",
    "You were signed out after a period of inactivity.": "د نه کارولو له امله تاسو له سیسټمه ووتلئ.",
    "Please fill in all fields.": "مهرباني وکړئ ټول تش ځایونه ډک کړئ.", "Passwords do not match.": "پټ نومونه سره یو شان نه دي.",
    "The new passwords do not match.": "نوي پټ نومونه سره یو شان نه دي.", "Please select a customer first.": "لومړی یو پېرودونکی وټاکئ.",
    "Select an account.": "یو حساب وټاکئ.", "Customer Details": "د پېرودونکي معلومات", "Notes": "یادښتونه",
    "All": "ټول", "Yes": "هو", "No": "نه", "OK": "سمه ده", "Search": "لټون", "Refresh": "تازه کول",
    "Export complete": "راپور خوندي شو", "Pending": "تر ارزونې لاندې", "Verified": "تایید شوی", "Rejected": "رد شوی",
}

# Prefer the terms people use when discussing everyday banking in Pashto.
# These overrides keep labels consistent across navigation, forms, tables and
# report choices while leaving database values in English.
_PS.update({
    "Bank Management System": "د بانک د چارو سمبالښت",
    "BANKING SYSTEM": "د بانکدارۍ چارې",
    "Customers": "مشتریان",
    "Customer": "مشتري",
    "Customer ID": "د مشتری پېژندشمېره",
    "Customer Details": "د مشتری معلومات",
    "Registered customers": "ثبت شوي مشتریان",
    "Customers registered": "ثبت شوي مشتریان",
    "Accounts of Selected Customer": "د ټاکل شوي مشتری حسابونه",
    "Find customer (ID or name)": "د مشتری نوم یا پېژندشمېره ولیکئ",
    "Enter customer ID or name": "د مشتری نوم یا پېژندشمېره ولیکئ",
    "Select a customer from the list to view their accounts.": "د حسابونو د لیدلو لپاره له لست څخه مشتری وټاکئ.",
    "Transactions": "راکړې ورکړې",
    "Recorded transactions": "ثبت شوې راکړې ورکړې",
    "All transactions": "ټولې راکړې ورکړې",
    "Transaction Counts": "د راکړې ورکړې شمېر",
    "Transaction Amounts": "د راکړې ورکړې پیسې",
    "Transaction type": "د راکړې ورکړې ډول",
    "Transaction Summary": "د راکړې ورکړې لنډیز",
    "Transaction Details": "د راکړې ورکړې جزیات",
    "Deposits": "حساب ته اچول شوې پیسې",
    "Withdrawals": "له حسابه ایستل شوې پیسې",
    "Transfers": "د حسابونو ترمنځ لېږد",
    "Reversals": "بېرته ګرځول شوې راکړې ورکړې",
    "deposit": "حساب ته پیسې اچول",
    "withdrawal": "له حسابه پیسې ایستل",
    "transfer": "د حسابونو ترمنځ لېږد",
    "reversal": "راکړه ورکړه بېرته ګرځول",
    "Deposit": "حساب ته پیسې اچول",
    "Withdrawal": "له حسابه پیسې ایستل",
    "Transfer": "د حسابونو ترمنځ لېږد",
    "Deposit / Withdraw": "پیسې اچول او ایستل",
    "History & Search": "د راکړې ورکړې مخینه او لټون",
    "Submit Transaction": "راکړه ورکړه ثبتول",
    "Reverse Selected...": "ټاکل شوې راکړه ورکړه بېرته ګرځول...",
    "Txn ID / ref": "د راکړې ورکړې شمېره",
    "Reference": "د راکړې ورکړې شمېره",
    "Balance": "پاتې پیسې",
    "Total Balance": "د ټولو حسابونو پاتې پیسې",
    "Current Balance": "اوسنۍ پاتې پیسې",
    "Stored Balance": "په سیستم کې ثبت شوې پیسې",
    "Ledger Balance": "د راکړې ورکړې له مخې پاتې پیسې",
    "Opening balance": "د حساب د پیل پیسې",
    "Opening balance (": "د حساب د پیل پیسې (",
    "Account Type": "د حساب ډول",
    "Savings": "د سپما حساب",
    "Checking": "د ورځنیو لګښتونو حساب",
    "Fixed Deposit": "د ټاکلې مودې سپما",
    "Interest": "د سپما ګټه",
    "Monthly Interest": "میاشتنۍ سپما ګټه",
    "Interest Credit": "حساب ته ورزیاته شوې ګټه",
    "Annual Rate": "د ګټې کلنۍ سلنه",
    "APR (%)": "د پور کلنۍ ګټه (سلنه)",
    "Principal": "د پور اصلي پیسې",
    "Amount Due": "ټولې بېرته ورکړل کېدونکې پیسې",
    "Disburse": "پور ورکول",
    "Record Repayment": "د پور بېرته ورکړه ثبتول",
    "Apply for Loan": "د پور غوښتنه کول",
    "Reject": "نه منل",
    "Approve": "منل",
    "admin": "د سیستم اداره کوونکی",
    "teller": "د بانک کارکوونکی",
    "viewer": "یوازې لوستونکی",
    "Role": "د کارن واک",
    "Staff Role": "د کارن واک",
    "Role: ": "د کارن واک: ",
    "Audit Log": "د سیستم د بدلونونو تاریخچه",
    "Filter (action, user, details)": "د کار، کارن یا جزیاتو له مخې لټون",
    "Search audit log...": "د سیستم د بدلونونو تاریخچه ولټوئ...",
    "KYC status": "د مشتری د پېژندنې حالت",
    "KYC verification": "د مشتری د پېژندنې ارزونه",
    "Save KYC Status": "د پېژندنې پایله خوندي کول",
    "pending": "تر ارزونې لاندې",
    "verified": "پېژندنه تایید شوې",
    "rejected": "پېژندنه نه ده تایید شوې",
    "Active": "فعال",
    "active": "فعال",
    "frozen": "موقتي بند",
    "closed": "تړل شوی",
    "Phone": "د ټیلیفون شمېره",
    "Phone *": "د ټیلیفون شمېره *",
    "Find": "پیدا کول",
    "Look up": "حساب پیدا کول",
    "Deactivate": "بندول",
    "Reactivate": "بېرته فعالول",
    "Freeze": "حساب موقتي بندول",
    "Unfreeze": "حساب بېرته فعالول",
    "From account": "له دې حسابه",
    "To account": "دې حساب ته",
    "Select an account.": "یو حساب وټاکئ.",
    "A reversal reason is required.": "د راکړې ورکړې د بېرته ګرځولو لامل ولیکئ.",
    "Confirm password": "پټ نوم بیا ولیکئ",
    "Update your account security": "د خپل حساب خوندیتوب تازه کړئ",
    "Choose a different new password.": "نوی پټ نوم له اوسني پټ نومه جلا وټاکئ.",
    "English": "انګلیسي",
    "All": "ټول",
    "Yes": "هو",
    "No": "نه",
    "Created (UTC)": "د جوړېدو نېټه",
    "Last login (UTC)": "د وروستي ننوتلو نېټه",
    "Time (UTC)": "وخت",
    "Applied (UTC)": "د ثبت نېټه",
    "Date/Time (UTC)": "نېټه او وخت",
    "Account no.": "د حساب شمېره",
    "Account No.": "د حساب شمېره",
    "Account number": "د حساب شمېره",
    "Account no., customer ID or name": "د حساب شمېره، د مشتری پېژندشمېره یا نوم",
    "ID, name or account no.": "پېژندشمېره، نوم یا د حساب شمېره",
    "Search customers": "مشتریان ولټوئ",
    "Search accounts": "حسابونه ولټوئ",
    "Search audit log...": "د سیستم د بدلونونو تاریخچه ولټوئ...",
    "Please fill in all fields.": "مهرباني وکړئ ټول ځایونه ډک کړئ.",
    "You were signed out after a period of inactivity.": "د اوږدې بې‌فعالۍ له امله له سیسټمه ووتلئ.",
    "Please select a customer first.": "لومړی مشتری وټاکئ.",
    "Find and select a customer first.": "لومړی مشتری پیدا او وټاکئ.",
    "No active customer matches that search.": "د لټون له مخې فعال مشتری پیدا نه شو.",
    "The selected customer was not found.": "ټاکل شوی مشتری پیدا نه شو.",
    "Customer verification is required before applying for a loan.": "د پور غوښتلو مخکې باید د مشتری پېژندنه تایید شي.",
    "An account cannot be opened until customer verification is complete.": "تر هغې حساب نه پرانیستل کېږي چې د مشتری پېژندنه تایید شوې نه وي.",
    "Transfer completed. Reference ": "پیسې بل حساب ته ولېږدول شوې. د راکړې ورکړې شمېره: ",
    "Source and destination accounts must be different.": "د پیسو د لېږلو او ترلاسه کولو حسابونه باید جلا وي.",
    # Report headings and values are assembled by the report service, so they
    # must be present here even though they are not widget literals.
    "Metric": "د راپور موضوع",
    "Count": "شمېر",
    "Total": "ټولټال",
    "Total (AFN)": "ټولې پیسې (افغانۍ)",
    "Amount (AFN)": "د پیسو اندازه (افغانۍ)",
    "Current Balance (AFN)": "اوسنۍ پاتې پیسې (افغانۍ)",
    "Accounts (opened in range)": "په دې موده کې پرانیستل شوي حسابونه",
    "Opening balances": "د حساب د پیل پیسې",
    "All transactions": "ټولې راکړې ورکړې",
    "Accounts opened": "پرانیستل شوي حسابونه",
    "Customers registered": "ثبت شوي مشتریان",
    "Account": "حساب",
    "Account Type": "د حساب ډول",
    "Stored Balance": "په سیستم کې ثبت شوې پاتې پیسې",
    "Ledger Balance": "د راکړې ورکړې له مخې پاتې پیسې",
    "Result": "پایله",
    "Mismatch": "توپیر شته",
    "OK": "سم دی",
    "From Account": "له حسابه",
    "To Account": "حساب ته",
    "Status": "حالت",
    "Note": "یادښت",
    "Amount": "د پیسو اندازه",
    "Period": "موده",
    "Paid": "ورکړل شوې پیسې",
    "Type": "د راکړې ورکړې ډول",
    "Leave a date empty for no limit. The Ledger Consistency Check and the current balances in Account Summary ignore dates. All times are UTC.": "که د نېټې ځای تش پرېږدئ، د وخت محدودیت به نه وي. د حسابونو د سمون کتنه او د حسابونو لنډیز د نېټو له محدودیت پرته ښودل کېږي. ټول وختونه د همغږې نړیوالې زمانې له مخې دي.",
    "Export report": "راپور خوندي کول",
    "Export report as PDF": "راپور د PDF په بڼه خوندي کول",
    "Loan Applications": "د پور غوښتنې",
    "Loan Repayments": "د پور بېرته ورکړې",
    "Interest Credits": "حساب ته جمع شوې ګټه",
    "Decision": "د غوښتنې پرېکړه",
    "Approve": "تاییدول",
    "Reject": "ردول",
    "Teller disbursement required": "د پور د جمع کولو لپاره د بانک کارکوونکی اړین دی",
    "Select a pending loan to approve or reject it. Approved loans must then be disbursed by a teller. Interest is estimated once from APR and term.": "د پور د غوښتنې د تایید یا رد لپاره، لومړی تر ارزونې لاندې پور وټاکئ. له تایید وروسته، د بانک کارکوونکی پور حساب ته جمع کوي. ګټه د کلنۍ کچې او مودې له مخې یو ځل اټکلېږي.",
    "Loan Ref": "د پور شمېره",
    "APR": "کلنۍ ګټه",
    "Months": "میاشتې",
    "Outstanding": "د پور پاتې پیسې",
    "Applied (UTC)": "د غوښتنې نېټه",
    "Disbursed (UTC)": "د پور د ورکړې نېټه",
    "Application Date (UTC)": "د پور غوښتنې نېټه",
    "Credit Date (UTC)": "حساب ته د ګټې د جمع کېدو نېټه",
    "Payment": "د بېرته ورکړې پیسې",
    "Credit": "حساب ته جمع شوې پیسې",
    "Notes": "یادښتونه",
})

# A few human labels and database enum values intentionally share similar
# translations. Prefer the stable lowercase enum value when returning a choice.
_PS_CHOICES = {
    _PS["opening"]: "opening",
    _PS["deposit"]: "deposit",
    _PS["withdrawal"]: "withdrawal",
    _PS["transfer"]: "transfer",
    _PS["reversal"]: "reversal",
}

_PATTERNS = (
    (re.compile(r"^Total \(([^)]+)\)$"), "ټولټال ({})"),
    (re.compile(r"^Amount \(([^)]+)\)$"), "د پیسو اندازه ({})"),
    (re.compile(r"^Current Balance \(([^)]+)\)$"), "اوسنۍ پاتې پیسې ({})"),
    (re.compile(r"^Principal \(([^)]+)\)$"), "د پور اصلي پیسې ({})"),
    (re.compile(r"^Amount Due \(([^)]+)\)$"), "ټولې بېرته ورکړل کېدونکې پیسې ({})"),
    (re.compile(r"^Paid \(([^)]+)\)$"), "ورکړل شوې پیسې ({})"),
    (re.compile(r"^Outstanding \(([^)]+)\)$"), "د پور پاتې پیسې ({})"),
    (re.compile(r"^Payment \(([^)]+)\)$"), "د بېرته ورکړې پیسې ({})"),
    (re.compile(r"^Credit \(([^)]+)\)$"), "حساب ته جمع شوې پیسې ({})"),
    (re.compile(r"^Customer (\d+) created\.$"), "مشتري {} ثبت شو."),
    (re.compile(r"^Customer (\d+) updated\.$"), "د مشتری {} معلومات بدل شول."),
    (re.compile(r"^Customer (\d+) deactivated\.$"), "د مشتری {} حساب غیرفعال شو."),
    (re.compile(r"^Customer (\d+) reactivated\.$"), "د مشتری {} حساب بېرته فعال شو."),
    (re.compile(r"^(\d+) row\(s\)\.$"), "{} کرښې."),
    (re.compile(r"^Transfer completed\. Reference (.+)$"), "پیسې ولېږدول شوې. د پېژندنې شمېره {}"),
    (re.compile(r"^Password must be at least (\d+) characters\.$"), "پټ نوم باید لږ تر لږه {} توري ولري."),
    (re.compile(r"^Password must be at most (\d+) bytes\.$"), "پټ نوم باید تر {} بایټو زیات نه وي."),
    (re.compile(r"^Password must have at least (\d+) characters, including a letter and a digit\.$"), "پټ نوم باید لږ تر لږه {} توري ولري او توري او شمېرې پکې وي."),
    (re.compile(r"^(.+) is required\.$"), "{} اړین دی."),
    (re.compile(r"^(.+) already exists\.$"), "{} له مخکې شته."),
)

_language = "en"


def set_language(language: str) -> None:
    global _language
    _language = language if language in LANGUAGES else "en"


def get_language() -> str:
    return _language


def tr(value):
    if not isinstance(value, str) or _language == "en":
        return value
    if value in _PS:
        return _PS[value]
    if value.isupper() and value.title() in _PS:
        return _PS[value.title()].upper()
    for pattern, replacement in _PATTERNS:
        match = pattern.match(value)
        if match:
            return replacement.format(*match.groups())
    return value


def untr(value):
    """Convert a translated choice back to its stable internal value."""
    if _language == "ps" and isinstance(value, str):
        if value in _PS_CHOICES:
            return _PS_CHOICES[value]
        for source, translated in _PS.items():
            if value == translated:
                return source
    return value


def install_widget_translation():
    """Translate visible CustomTkinter properties while preserving their values."""
    import customtkinter as ctk
    if getattr(ctk, "_bms_i18n_installed", False):
        return
    ctk._bms_i18n_installed = True
    for cls in (ctk.CTkLabel, ctk.CTkButton, ctk.CTkEntry, ctk.CTkComboBox,
                ctk.CTkCheckBox, ctk.CTkRadioButton, ctk.CTkTextbox,
                ctk.CTkOptionMenu, ctk.CTkTabview):
        init = cls.__init__
        def translated_init(self, *args, __init=init, __cls=cls, **kwargs):
            for key in ("text", "placeholder_text", "label_text"):
                if key in kwargs:
                    kwargs[key] = tr(kwargs[key])
            if "values" in kwargs:
                kwargs["values"] = [tr(v) for v in kwargs["values"]]
            if _language == "ps":
                if __cls in (ctk.CTkLabel, ctk.CTkEntry, ctk.CTkComboBox):
                    kwargs["justify"] = "right"
                if __cls is ctk.CTkLabel and kwargs.get("anchor") != "center":
                    kwargs["anchor"] = "e"
                if __cls in (ctk.CTkButton, ctk.CTkOptionMenu):
                    kwargs["anchor"] = "e"
            __init(self, *args, **kwargs)
            if _language == "ps" and __cls in (ctk.CTkCheckBox, ctk.CTkRadioButton):
                self._text_label.configure(anchor="e", justify="right")
            if _language == "ps" and __cls is ctk.CTkTextbox:
                self._textbox.configure(justify="right")
        cls.__init__ = translated_init
        configure = cls.configure
        def translated_configure(self, *args, __configure=configure, __cls=cls, **kwargs):
            for key in ("text", "placeholder_text", "label_text"):
                if key in kwargs:
                    kwargs[key] = tr(kwargs[key])
            if "values" in kwargs:
                kwargs["values"] = [tr(v) for v in kwargs["values"]]
            if _language == "ps":
                if __cls in (ctk.CTkLabel, ctk.CTkEntry, ctk.CTkComboBox):
                    kwargs["justify"] = "right"
                if __cls is ctk.CTkLabel and kwargs.get("anchor") != "center":
                    kwargs["anchor"] = "e"
                if __cls in (ctk.CTkButton, ctk.CTkOptionMenu):
                    kwargs["anchor"] = "e"
            if _language == "ps" and __cls in (ctk.CTkCheckBox, ctk.CTkRadioButton):
                self._text_label.configure(anchor="e", justify="right")
            if _language == "ps" and __cls is ctk.CTkTextbox:
                self._textbox.configure(justify="right")
            return __configure(self, *args, **kwargs)
        cls.configure = translated_configure
    add_tab = ctk.CTkTabview.add
    def translated_add(self, name, *args, **kwargs):
        # Keep CTkTabview's internal key stable for .tab(name) and callbacks;
        # translate only the visible segmented-button label.
        tab = add_tab(self, name, *args, **kwargs)
        button = self._segmented_button._buttons_dict.get(name)
        if button is not None:
            button.configure(text=tr(name))
        return tab
    ctk.CTkTabview.add = translated_add
    title_method = ctk.CTkToplevel.title
    def translated_title(self, text=None):
        return title_method(self) if text is None else title_method(self, tr(text))
    ctk.CTkToplevel.title = translated_title
    # Tk's built-in dialogs are used alongside CustomTkinter controls.
    from tkinter import filedialog, messagebox, simpledialog
    for module, names, keys in (
        (messagebox, ("showerror", "showwarning", "showinfo", "askyesno"), (0, 1)),
        (filedialog, ("asksaveasfilename", "askopenfilename"), ()),
        (simpledialog, ("askstring",), (0, 1)),
    ):
        for name in names:
            original = getattr(module, name)
            def translated_dialog(*args, __original=original, __keys=keys, **kwargs):
                args = list(args)
                for index in __keys:
                    if index < len(args):
                        args[index] = tr(args[index])
                if "title" in kwargs:
                    kwargs["title"] = tr(kwargs["title"])
                return __original(*args, **kwargs)
            setattr(module, name, translated_dialog)


def add_language_selector(parent, command, **grid_options):
    """Add a compact language picker whose values are UI labels only."""
    import customtkinter as ctk
    import tkinter as tk

    variable = tk.StringVar(value=tr(LANGUAGES[get_language()]))

    def selected(label):
        command("ps" if label in ("پښتو", "Pashto") else "en")

    picker = ctk.CTkOptionMenu(
        parent,
        variable=variable,
        values=["English", "پښتو"],
        command=selected,
        width=110,
        height=30,
    )
    if grid_options:
        picker.grid(**grid_options)
    else:
        picker.pack()
    return picker

