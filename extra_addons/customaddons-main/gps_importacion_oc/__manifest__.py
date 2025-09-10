# -*- coding: utf-8 -*-
{
    'name': "Importacion Purchase Order",

    'summary': """
        Cambios en cuentas contables para importaciones en las recepciones""",

    'description': """
        Cambios en cuentas contables para importaciones en las recepciones
    """,

    'author': "Washington Guijarro",
    'website': "https://gpsgroup.com.ec",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Purchase',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'purchase','product'],

    # always loaded
    'data': [
        'views/product_category.xml',
    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}
