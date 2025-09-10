{
    'name': 'Calendar Approval',
    'version': '16.0.1.0.0',
    'category': 'Calendar',
    'summary': 'Un solo calendario, salas con responsable, usuario no edita tras crear, responsable aprueba/rechaza.',
    'depends': ['calendar', 'mail','bi_meeting_from_task'],
    'data': [
        'security/security.xml',
        'views/calendar_room_views.xml',
        'views/calendar_event_views.xml',
    ],
    'installable': True,
    'application': False,
}
