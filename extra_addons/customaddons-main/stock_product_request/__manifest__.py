# -*- coding: utf-8 -*-
{
    "name": "Stock - Product Request",
    "version": "16.0.1.0.2",
    "author": "Fabrica de software libre",
    "website": "www.libre.ec",
    "depends": [
        "base_multi_company",
        "report_xlsx",
        "stock_move_line_auto_fill",
        "stock_picking_mass_action",
        "stock_quant_manual_assign",
        "stock_security",
    ],
    "data": [
        "data/ir_sequence.xml",
        "security/stock_security.xml",
        "security/ir.model.access.csv",
        "reports/reports.xml",
        # "report/report_deliveryslip.xml",
        "reports/stock_request.xml",
        "views/stock.xml",
        # "views/stock_request_product.xml",
        # "wizards/stock_request.xml",
    ],
    "installable": True,
}
