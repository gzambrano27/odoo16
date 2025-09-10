{
    'name': 'Maestro Histórico GPS',
    'version': '1.0',
    'category': 'Inventory',
    'author': 'Guillermo Zambrano',
    'website': 'https://produccion.gpsgroup.ec/',
    'depends': ['base', 'stock', 'purchase', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_historical_gps_views.xml',
        'views/sale_historical_gps_views.xml',
        'views/inventory_historical_gps_views.xml',
        'views/menu_items.xml',
    ],
    'images': [
        'static/description/logo.png',
        'static/description/icon.png',
    ],  # Ruta a la imagen del logo
    'installable': True,
    'auto_install': False,
    'application': True,
}
