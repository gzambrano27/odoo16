# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Año fiscal",
     'version': '1.0',
    "category": "Localizacion",
    'license': 'LGPL-3',
    "author": "Lajonner Crespin",
    'summary': "Localizacion Periodos fiscales",
    'description': """
    
    
    """,
    'website': None,
    'depends': ['account_accountant','calendar_days','bi_purchase_advance_payment','gps_payment'],
    "data": [

        'security/ir.model.access.csv',
        'security/res_groups.xml',

        "views/account_fiscal_year_line.xml",
        "views/account_fiscal_year.xml",

        "views/account_move.xml",
        "views/account_payment.xml",
        "views/stock_picking.xml",

        "views/ir_ui_menu.xml",
        
    ],
    'assets': {
    
    },
}
