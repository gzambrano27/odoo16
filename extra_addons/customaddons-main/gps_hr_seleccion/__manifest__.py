# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "Equipos para seleccion",
    "author": "Washington Guijarro",
    "version": "16.0.2.0.3",
    "summary": "Usa este modulo para asignar equipos al aspirante ",
    "website": "https://gpsgroup.com.ec",
    "category": "Seleccion",
    "depends": ["hr_recruitment","mail","base"],
    "data": ["security/requisicion_personal_groups.xml",
            "security/requisicion_personal_rules.xml",
            'security/ir.model.access.csv',
            'views/hr_applicant_views.xml',
            'views/requisicion_personal_views.xml',
    ],
    "demo": ["demo/purchase_request_demo.xml"],
    "license": "LGPL-3",
    "installable": True,
    "application": True,
}
