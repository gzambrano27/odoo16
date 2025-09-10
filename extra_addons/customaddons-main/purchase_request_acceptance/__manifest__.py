# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Macro Purchase Request Acceptance",
    "version": "16.0.1.0.0",
    "category": "Purchase Management",
    "author": "Washington Guijarro",
    "license": "AGPL-3",
    "website": "https://gpsgroup.com.ec",
    "depends": ["purchase",  "base", "macro_purchase_request",'product','stock','analytic','purchase_request'],
    "data": [
        "data/work_acceptance_sequence.xml",
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/macro_purchase_request_views.xml",
        "views/res_config_settings_views.xml",
        "views/request_acceptance_views.xml",
        "wizard/wizard_generate_pr_view.xml",
        "wizard/select_request_acceptance_wizard_views.xml",
        "wizard/request_accepted_date_wizard.xml",
    ],
    "installable": True,
    "application": True,
}
