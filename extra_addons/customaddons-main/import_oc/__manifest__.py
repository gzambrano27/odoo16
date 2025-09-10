# -*- coding: utf-8 -*-
{
    'name': "Import Purchase Order",

    'summary': """
        Import Purchase Order from Excel file""",

    'description': """
        Import Purchase Order from Excel file
    """,

    'author': "forestdbs",
    'website': "https://www.forestdbs.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Purchase',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'purchase'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizzard/wizard_import_oc.xml',
    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}
