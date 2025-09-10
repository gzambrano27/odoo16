# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Advance Down Payment on Purchase Order',
    'version': '16.0.0.1',
    'category': 'Purchase',
    'summary': 'Purchase Down payment for purchase order advance payment purchase advance payment purchase order advance payment for purchase advance payment for purchase order down payment advance down payment for purchase order add advance payment from purchase order',
    'description': """

        Purchase Order Advance Payment in odoo,
        Make an Advance Payment from Purchase Order in odoo,
        Advance Payment in odoo,
        Advance Payments will be Listed in Payment Advance Tab in odoo.
        Advance Payment Wizard in odoo,
        Outstanding Debits balance in odoo,
 
    """,
    'author': 'BrowseInfo',
    "price": 9,
    "currency": 'EUR',
    'website': 'https://www.browseinfo.com',
    'depends': ['purchase','account','stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/advance_payment_views.xml',
        'views/purchase_views.xml',
    
    ],
    'license':'OPL-1',
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'live_test_url': 'https://youtu.be/yNPojYhysNw',
    "images": ['static/description/Banner.gif'],
}
