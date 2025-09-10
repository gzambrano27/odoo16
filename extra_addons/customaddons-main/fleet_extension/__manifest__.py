{
    'name': 'Extension de Flota',
    'version': '1.0',
    'category': 'Human Resources',
    'author': 'matheu',
    'depends': ['base', 'fleet'],
    'data': [
        "views/fleet_vehicle_view.xml",
        "views/travel_address_views.xml",
        "views/travel_route_views.xml",
        "views/menu_fleet.xml",
        "data/maintenance_data.xml",
        'security/ir.model.access.csv',
    ],


    'installable': True,  # Define si el módulo se puede instalar. Si es True, el módulo es instalable.
    'application': True,  # Si es True, el módulo aparecerá en la vista de aplicaciones de Odoo.
    'auto_install': False,  # Define si el módulo debe instalarse automáticamente si se cumplen sus depen
}
