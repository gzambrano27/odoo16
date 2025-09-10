{
    'name': 'Solicitud de Aprobación de Atenciones Comerciales',
    'version': '1.0',
    'author': 'Tu Empresa',
    'category': 'Custom',
    'depends': ['base', 'contacts', 'hr'],
    'data': [
        'security/security.xml',            # Definición de grupos
        'security/ir.model.access.csv',       # Reglas de acceso
        'data/ir_sequence.xml',
        'reports/solicitud_comercial.xml',
        'views/solicitud_views.xml',
        'views/menu_items_views.xml',
        'wizard/confirmar_fecha_salida_view.xml',
    ],
    'installable': True,
    'application': True,
}
