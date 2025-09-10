{
    'name': 'Maintenance Add Actas',
    'version': '1.0',
    'summary': 'Extensión del módulo de mantenimiento para agregar actas',
    'author': 'Guillermo Zambrano',
    'depends': ['maintenance','portal'],
    'data': [
        'data/data.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/maintenance_equipment_view.xml',  # Vistas
        'views/maintenance_actas_views.xml',  # Vistas
        'views/menu_item_views.xml',  # Menús y acciones
        'views/hr_employee.xml',
        'report/report.xml',
        'report/report_equipment_entrega.xml',
        'report/report_equipment_recepcion.xml',
    ],
    'installable': True,
    'application': False,
}
