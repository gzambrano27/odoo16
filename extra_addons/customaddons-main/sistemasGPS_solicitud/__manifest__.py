{
    'name': 'Servicio de Asistencia Odoo',
    'version': '1.0',

    'description': """
        Este módulo permite a los usuarios crear solicitudes de servicio o asistencia, dedicado al desarrollo del sistema Odoo.
    """,
    'author': 'Matheu Zambrano',
    'category': 'Services',
    'depends': ['base', 'hr', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/solicitud_servicio_view.xml',
        'views/correos_primordialesodoo_views.xml',

    ],
    'icon': 'static/description/ICONO.PNG',
    'installable': True,
    'application': True,
}
