# -*- coding: utf-8 -*-
{
    "name": "Bank Statement Reconciliation",
    "summary": "Reconciliation, Bank Reconciliation, Invoice Reconciliation, Payment "
    "Reconciliation, Bank Statement",
    "description": """
        * Bank Statement Reconciliation
    """,
    "author": "Openinside",
    "license": "OPL-1",
    "website": "https://www.open-inside.com",
    "price": 159.0,
    "currency": "USD",
    "category": "Accounting",
    "version": "16.0.1.3.1",
    "depends": ["account", "account_check_printing"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_bank_statement.xml",
        "views/account_bank_statement_line.xml",
        "views/account_payment.xml",
        "views/account_move_line.xml",
        "views/account_journal.xml",
        "views/action.xml",
        "views/menu.xml",
        "reports/account_bank_statement.xml",
        "reports/main.xml",
        "wizards/account_bank_statement_generate.xml",
        "wizards/account_bank_statement_helper.xml",
    ],
    "odoo-apps": True,
    "auto_install": False,
    "images": ["static/description/cover.png"],
    "application": False,
}
