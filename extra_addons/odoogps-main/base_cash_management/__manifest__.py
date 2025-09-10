#!/usr/bin/env python
{
    "name": "Base - Cash Management",
    "version": "16.0.1.0.2",
    "summary": "Base module for the creation of different cash management formats",
    "category": "Accounting",
    "author": "nextgen.ec",
    "maintainer": "NextGen S.A.",
    "website": "https://nextgen.ec",
    "license": "AGPL-3",
    "contributors": ["NextGen S.A."],
    "depends": [
        "base",
        "account",
        "account_payment_order",
        "account_payment_order_notification",
    ],
    "data": ["security/ir.model.access.csv", "views/account.xml", "views/res_bank.xml"],
    "installable": True,
    "auto_install": False,
    "application": False,
}
