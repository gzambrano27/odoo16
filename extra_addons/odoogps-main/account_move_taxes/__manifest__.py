# Copyright (C) 2019 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Account - Taxes",
    "summary": "Show tax summary and edit taxes on account move lines",
    "version": "16.0.1.0.2",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "NextGen-ec",
    "website": "https://github.com/OCA/account-financial-tools",
    "depends": ["account", "l10n_latam_invoice_document", "account_tax_one_vat"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move.xml",
        "wizards/account_move_edit_taxes.xml",
    ],
}
