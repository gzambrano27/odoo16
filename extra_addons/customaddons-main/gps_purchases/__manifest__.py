{
    'name': 'Funcionalidades adicionales para las OC',
    'version': '1.0',
    'category': 'Se agrega funciones complementarias para las OC incluidas los controladores',
    'description': """

    """,
    'author': "GPS",
    'website': '',
    'depends': [
         'gps_estados_purchase','gps_reports','purchase','stock','report_xlsx',
    ],
    'data': [
        'data/ir_config_parameter.xml',
        'views/account_payment_term.xml',
        'views/purchase_order.xml',
        'views/guarantee_order.xml',
        'views/product_product_tree.xml',
        #'views/stock_move_line_views.xml',
        'views/stock_picking_views.xml',
        'report/purchase_report_templates.xml',
        'views/purchase_product_period_report_form.xml',
        'views/purchase_product_period_report_views.xml',
        'views/purchase_transit_inventory_report_form.xml',
        'views/purchase_transit_inventory_report_views.xml',
        'views/purchase_payment_report_views.xml',
        'views/product_age_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}