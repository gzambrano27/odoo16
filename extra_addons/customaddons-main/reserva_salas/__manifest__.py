{
    'name': 'Reserva de Salas de Reuniones',
    'version': '1.0',
    'summary': 'Gestión de reservas de salas de reuniones',
    'description': """
        Este módulo permite a los usuarios reservar salas de reuniones con un flujo de aprobación.
        Los usuarios pueden crear reservas, mientras que los administradores pueden aprobar o rechazar.
    """,
    'author': 'Matheu Zambrano',
    'category': 'Services',
    'depends': ['base', 'hr', 'mail', 'calendar'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/reserva_sala_views.xml',
        'views/sala_views.xml',
        'views/correos_primordiales_views.xml',
    ],

    'installable': True,
    'application': True,
}