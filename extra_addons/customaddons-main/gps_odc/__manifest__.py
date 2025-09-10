{
    'name': 'ODC Templates',
    'version': '1.0.0.0.0',
    'summary': 'Módulo de ODC Templates',
    'category': 'Extra Tools,Accounting,Purchases,Sales,Project,Productivity',
    'author': 'Blanca Pérez',
    'license': 'LGPL-3',
    'depends': [
        'xf_excel_odoo_connector'
    ],
    'data': [
        'data/module_categories.xml',
        'views/odc_template.xml',
    ],
    #'images': ['static/description/icono.png'],

    #'icon': 'ticketera_gps/static/description/icono.png',
    'installable': True,
    'application': True,
}
