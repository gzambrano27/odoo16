{
    'name': 'Vistas de Datos POWER BI Otros,..etc',
    'version': '1.0',
    'category': 'Se agrega vistas para ser usadas en consultas',
    'description': """

    """,
    'author': "GPS",
    'website': '',
    'depends': [
        'gps_bancos','base'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/accounts_receivable_view.xml',
        'views/accounts_payable_view.xml',
        'views/accounts_analytic_view.xml',
        'views/purchase_order_view.xml',
        'views/account_move_view.xml',

        'views/account_account.xml',

        'views/ir_ui_menu.xml',

    ],
    'installable': True,
}
