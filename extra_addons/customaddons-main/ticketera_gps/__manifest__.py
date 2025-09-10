{
    'name': 'Ticketera GPS',
    'version': '16.0.1.0.0',
    'summary': 'Módulo de Tickets GPS con chatter y portal',
    'category': 'Services',
    'author': 'Matheu Zambrano',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'mail',
        'portal',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/ticket_views.xml',
        'data/ticket_sequence.xml',
    ],
    'images': ['static/description/icono.png'],

    'icon': 'ticketera_gps/static/description/icono.png',
    'installable': True,
    'application': True,
}
