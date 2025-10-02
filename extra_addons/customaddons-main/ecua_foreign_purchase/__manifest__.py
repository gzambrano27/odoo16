{
    'name': 'Foreign Purchases Ecuador',
    'version': '1.0',
    'category': 'Generic Modules/Purchases',
    'description': """
Importations Management
========================

Improve purchase orders to control imports
    """,
    'author': "Washington Guijarro",
    'website': 'https://www.gpsgroup.com.ec',
    'depends': [
        'purchase',
        'stock_landed_costs',
        'account_payment_purchase',
        'report_xlsx',
    ],
    'data': [
        'security/foreign_security.xml',
        'security/ir.model.access.csv',
        'data/l10n_ec_landed_cost_data.xml',
        'data/importation_gastos_data.xml',
        'data/regimen_data.xml',
        'data/transportation_data.xml',
        'data/type.arancel.csv',
        'data/purchase.tariff.csv',
        'security/foreign_security.xml',
        'security/ir.model.access.csv',
        'report/reports.xml',
        'views/purchase_tariff_view.xml',
        'views/trade_importation_view.xml',
        'views/account_move.xml',
        'views/product_view.xml',
        'views/purchase_concept_bill.xml',
        'views/res_config_settings.view.xml',
        'views/product_category.view.xml',
        'views/menu_foreign.xml',
        'views/importation_advance_view.xml',
        'wizard/wizard_purchase_order_assing.xml',
        'report/report_foreign_trade.xml',
        'data/ir_sequence_data.xml',

    ],
    'installable': True,
}
