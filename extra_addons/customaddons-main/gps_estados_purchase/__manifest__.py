# -*- coding: utf-8 -*-
{
    'name': "Nuevos estados en Purchase Order",

    'summary': """
        Se agrega nuevos estados en la orden de compra""",

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
    'depends': ['base', 'purchase','account_payment_purchase','purchase_request'],

    # always loaded
    'data': ['security/ir.model.access.csv',
        'views/purchase_order_view.xml',
        'views/purchase_order_state_log.xml'
    ],
}
