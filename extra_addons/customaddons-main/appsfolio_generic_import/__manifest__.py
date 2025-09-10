# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of appsfolio. (Website: www.appsfolio.in).                            #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

{
    'name': 'Odoo all import for Sales, Purchase, Invoice, Inventory, Pricelist, BOM, Payment, Journal Entry, Picking, '
            'Product, Customer, Chart of Account',
    'version': '16.0.1.0',
    'summary': 'Odoo import Data Import All in one import Invoice import Sales import Inventory import Purchase import '
               'stock inventory import Picking import Product image import Customer import serial import journal entry import payment import chart of account',
    'description': """
        import Invoice 
        import Sales 
        import Inventory 
        import Purchase 
        import stock inventory 
        import Picking 
        import Product 
        image import 
        Customer import 
        serial import journal entry 
        import payment 
        import chart of account""",
    'depends': ['base', 'sale_management', 'account_accountant', 'mrp', 'purchase', 'stock',
                'product_expiry'],
    'category': 'Extra Tools',
    'author': 'AppsFolio',
    'website': 'www.appsfolio.in',
    'data': [
        'security/import_security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'wizard/account_bank_statement_wizard_view.xml',
        'wizard/account_move_line_wizard_view.xml',
        'wizard/account_move_wizard_view.xml',
        'wizard/account_payment_wizard_view.xml',
        'wizard/import_invoice_wizard_view.xml',
        'wizard/mrp_bom_wizard_view.xml',
        'wizard/product_pricelist_wizard_view.xml',
        'wizard/product_product_wizard_view.xml',
        'wizard/product_supplierinfo_wizard_view.xml',
        'wizard/product_variant_wizard_view.xml',
        'wizard/purchase_order_line_wizard_view.xml',
        'wizard/purchase_order_wizard_view.xml',
        'wizard/res_partner_wizard_view.xml',
        'wizard/sale_order_line_wizard_view.xml',
        'wizard/sale_order_wizard_view.xml',
        'wizard/sale_pricelist_wizard_view.xml',
        'wizard/stock_picking_wizard_view.xml',
        'wizard/stock_quant_wizard_view.xml',
        'wizard/vendor_pricelist_wizard_view.xml',
        'wizard/wizard_chart_of_account_view.xml',
        'views/account_account_view.xml',
        'views/account_move.xml',
        'views/account_payment.xml',
        'views/generate_inv_view.xml',
        'views/mrp_bom.xml',
        'views/product_pricelist.xml',
        'views/product_product.xml',
        'views/product_template.xml',
        'views/purchase_order.xml',
        'views/res_partner.xml',
        'views/sale_order.xml',
        'views/stock_picking.xml',
        'views/stock_quant.xml',
        'views/import_dashboard.xml',
        'views/menu.xml',
    ],
    'price': 68.02,
    'currency': 'EUR',
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'OPL-1',
}
