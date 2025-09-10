# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Payments Files',
    'version' : '16.0.1.1',
    'summary': 'Payments',
    'sequence': 1,
    "author": "Washington Guijarro",
    'description': """
Payments
====================
    """,
    'category' : 'Finance',
    'images' : [],
    'depends' : ['account','base'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        
        'wizard/account_payment_multi_report.xml',
        "views/account_payment_views.xml",

        #'wizard/archivo_cheques_multi_posfechado.xml',
    ],
    # 'controllers': [
    #     'controllers/main.py',
    # ],
    'demo': [
        
    ],
    'qweb': [
        
    ],
    'installable': True,
    'auto_install': False,
}
