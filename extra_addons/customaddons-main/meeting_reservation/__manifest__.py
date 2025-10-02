{
    'name': 'Meeting Reservation',
    'version': '1.0',
    'summary': 'Gestión de reservas de salas de reuniones.',
    'author': 'Matheu Zambrano',
    'depends': ['base', 'mail', 'hr', 'calendar'],
    'data': [
        'security/meeting_security.xml',
        'security/ir.model.access.csv',
        'views/wizard_cancel_meeting_view.xml',
        'views/meeting_view.xml',
        'views/meeting_room_view.xml',
        'views/meeting_report_view.xml',
        'views/meeting_menu.xml',
    ],
    'installable': True,
    'application': True,
}