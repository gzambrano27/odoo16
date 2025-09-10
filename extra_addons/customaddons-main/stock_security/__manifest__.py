#!/usr/bin/env python
{
    "name": "Stock - Security",
    "version": "16.0.1.0.1",
    "category": "Inventory/Security",
    "summery": "Manage access to warehouse, Operation Type and product creation.",
    "depends": ["stock"],
    "data": [
        "security/res_groups.xml",
        "views/res_users.xml",
        # "views/stock.xml",
    ],
    "images": ["static/description/banner.png"],
    "license": "OPL-1",
    "installable": True,
    "application": True,
    "auto_install": False,
}
