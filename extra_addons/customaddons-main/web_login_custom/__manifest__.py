# -*- coding: utf-8 -*-
{
    "name": "Web Login - Email Identificación",
    "summary": "Cambia el label y el placeholder del login a 'Identificación'.",
    "version": "16.0.1.0.0",
    "category": "Web",
    "author": "GPS Sistemas",
    "website": "",
    "license": "LGPL-3",
    "depends": ["web",'base', 'portal'],
    "data": [
        "views/web_login.xml",
        'views/res_company.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'web_login_custom/static/src/css/bg_image.scss',
        ],
        "web.assets_frontend_minimal": [
            "web_login_custom/static/src/css/login.scss",
        ],
    },
    "installable": True,
    "application": False,
}
