# -*- coding: utf-8 -*-
{
    'name': "open_tarifarios",

    'summary': """
        Tarifarios    
    """,

    'description': """
        Tarifarios
    """,

    'author': "forestdbs",
    'website': "https://www.forestdbs.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Payroll Localization',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/tipo_roles.xml',
        'views/establecimientos.xml',
        'views/hr_sectores.xml',
    ],
    'installable':True,
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}
