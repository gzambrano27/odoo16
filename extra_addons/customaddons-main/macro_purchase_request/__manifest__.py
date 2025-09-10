# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "Macro Purchase Request",
    "author": "Washington Guijarro",
    "version": "16.0.2.0.3",
    "website": "https://gpsgroup.com.ec",
    "category": "Purchase Management",
    "depends": ["base",'mail','product','stock','sale','analytic','product_brand'],
    "data": [
        "security/macro_purchase_request_groups.xml",     # ← define los grupos aquí primero
    "security/ir.model.access.csv",                   # ← luego define los permisos con esos grupos
    "data/macro_purchase_request_sequence.xml",
    "security/macro_purchase_request_rules.xml",
    "views/macro_purchase_request_view.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": True,
}
