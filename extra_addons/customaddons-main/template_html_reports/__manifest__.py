# -*- coding: utf-8 -*-
{
    'name': "Reportes HTML GPS",

    'summary': """
        Reportes HTML para GPS""",

    'description': """
        Modulo para generar reportes HTML para GPS
    """,

    'author': "Forestdbs",
    'website': "https://www.forestdbs.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Utilities',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/main_menu.xml',
        'views/report_html_views.xml',
    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}
