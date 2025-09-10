# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Ajustes de Inventario",
    "version": "1.0",
    "description": """

""",
    "author": "GPS",
    "category": "Inventario",
    "depends": [
        "stock",'base','account_payment_purchase','portal',"stock_analytic",'stock_force_date_app','stock_account'
    ],
    'license': 'LGPL-3',
    "data": [
        #'security/stock_move_line_rule.xml',
        'data/sequence.xml',
        'security/groups.xml',
        'data/stock_quant_history.xml',
        'data/module_categories.xml',
        'security/ir.model.access.csv',
        'reports/ir_actions_report_xml.xml',
        'reports/reporte_inventory_adjustment.xml',
        'reports/report_in_out.xml',
        'reports/report_in_out_general.xml',
        'wizard/stock_inventory_report.xml',
        'wizard/inventory_document_adjust_wizard.xml',
        'wizard/inventory_document_transfer_wizard.xml',
        'wizard/stock_picking_import_wizard.xml',
        'wizard/view_stock_quantity_history.xml',
        'wizard/stock_immediate_transfer.xml',
        'wizard/stock_backorder_confirmation.xml',
        'views/inventory_document_adjust.xml',
        'views/inventory_document_adjust_line.xml',
        'views/inventory_document_transference.xml',
        'views/res_company.xml',
        'views/stock_picking.xml',
        'views/stock_quant_views.xml',
        'views/stock_quant_history.xml',
		'views/stock_cost_history.xml',
		'views/stock_move_line_views.xml',
        'views/product_product.xml',
        'views/ir_ui_menu.xml',
    ],
    'assets': {
    
    },
}
