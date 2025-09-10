# -*- coding: utf-8 -*-
{
    "name": "Account - Payment Advanced management",
    "summary": """Prepayment - Advance payments must go to a temporary account until they are assigned to an invoice.
                  Batch Payment - Manage payment to multiple invoices with a single record """,
    "version": "16.0.1.0.3",
    "author": "Fabrica de Software Libre,Odoo Community Association (OCA)",
    "maintainer": "Fabrica de Software Libre",
    "website": "http://www.libre.ec",
    "license": "AGPL-3",
    "category": "Account",
    "depends": ["account", "account_payment_residual_amount"],
    "data": [
        "security/ir.model.access.csv",
        "views/account.xml",
        "views/res_config.xml",
        "wizards/prepayment_assignment.xml",
        "wizards/payment_import_invoices.xml",
    ],
    "demo": [],
    "test": [],
    "installable": True,
}
