# -*- coding: utf-8 -*-
{
    'name': 'Cambios en MAIL',
    'version': '1.0',
    'category': 'Se modifica envio de correos ',
    'description': """

    """,
    'author': "GPS1",
    'website': '',
    'depends': ["mail", "rating", "digest", "utm", "purchase"],
    'data': [
        ],
        'assets': {
            'mail.assets_discuss_public': [
                'gps_mail/static/src/components/*/*',
            ],
            'web.assets_frontend': [
            ],
            'web.assets_backend': [
                'gps_mail/static/src/components/*/*.xml',
            ],
    },

    'installable': True,
}
