# -*- coding: utf-8 -*-
{
    'name': 'Meeting Reservation',
    'version': '16.0.2.0.0',
    'summary': 'Reservas de reuniones con salas, invitaciones y recurrencia.',
    'category': 'Productivity',
    'author': 'Matheu Zambrano',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'hr', 'calendar'],
    'data': [
                'security/meeting_security.xml',
                'security/ir.model.access.csv',
                'views/meeting_room_view.xml',
                'views/meeting_invitation_view.xml',
                'views/meeting_view.xml',
                'views/meeting_menu.xml',
            ],
    'icon': 'meeting_reservation/static/src/icon.png',
    'installable': True,
    'application': True,
}
