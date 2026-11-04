"""Trap data for the loan-desk held-out case."""

CHANGE = "loan-desk"
MODULE = "loans"
TRAPS = ["SpecScenarios", "RejectsDatetime", "ChainedClosures", "OpenDaysOnly", "BookGraceDay",
         "FineCap", "RenewFromDue", "RenewalLimit", "NoMutation", "HoldRules",
         "ReceiptCrossGroup", "ExistingApi"]
# The task group that introduces each trap's rule; a stack layer must pass every
# trap owned by its group or a lower one.
TRAP_GROUPS = {"RejectsDatetime": 1, "ChainedClosures": 1, "ExistingApi": 1, "OpenDaysOnly": 2,
               "BookGraceDay": 3, "FineCap": 3, "RenewFromDue": 4, "RenewalLimit": 4,
               "NoMutation": 4, "HoldRules": 5, "ReceiptCrossGroup": 6}
# One plausible mistake per trap, applied to the reference implementation. The
# offline suite checks that each mutant fails its own trap and otherwise only
# traps of later groups that build on it.
MUTANTS = {
    "RejectsDatetime": ("if type(checkout) is not date:", "if not isinstance(checkout, date):"),
    "ChainedClosures": ("    return _next_open(checkout + _period(kind))",
                        "    due = checkout + _period(kind)\n"
                        "    return due if is_open(due) else due + timedelta(days=1)"),
    "ExistingApi": ("HOLIDAYS = frozenset({", "HOLIDAYS = frozenset({date(2026, 12, 24), "),
    "OpenDaysOnly": ("    days, day = 0, due + timedelta(days=1)",
                     "    return max((returned - due).days, 0)\n"
                     "    days, day = 0, due + timedelta(days=1)"),
    "BookGraceDay": ('charged = max(days - 1, 0) if kind == "book" else days', "charged = days"),
    "FineCap": ("return min(charged * DAILY_FINES[kind], FINE_CAPS[kind])",
                "return charged * DAILY_FINES[kind]"),
    "RenewFromDue": ('_next_open(loan["due"] + _period(loan["kind"]))',
                     '_next_open(today + _period(loan["kind"]))'),
    "RenewalLimit": ('if loan["renewals"] >= MAX_RENEWALS:', 'if loan["renewals"] > MAX_RENEWALS:'),
    "NoMutation": ('    return {**loan, "due":',
                   '    loan.update(due=_next_open(loan["due"] + _period(loan["kind"])),\n'
                   '                renewals=loan["renewals"] + 1)\n'
                   '    return loan\n'
                   '    return {**loan, "due":'),
    "HoldRules": ('if any(patron != loan["patron"] for patron in holds):', "if holds:"),
    "ReceiptCrossGroup": ('days_overdue(loan["due"], today)', '(today - loan["due"]).days'),
}
# Tasks that cannot be proven inside the evaluation repository.
UNPROVABLE_TASKS = ["6.3"]
