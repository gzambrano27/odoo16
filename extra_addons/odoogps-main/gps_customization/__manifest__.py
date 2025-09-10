{
    "name": "GPS Customization",
    "version": "16.0.1.0.1",
    "category": "Uncategorized",
    "summary": "Custom fields for gps",
    "license": "AGPL-3",
    "author": "Juany Davila",
    "installable": True,
    "auto_install": False,
    "depends": ["mrp", "mrp_analytic", "material_purchase_requisitions"],
    "data": [
        'views/mrp_bom_view.xml',
        'views/mrp_production.xml',
        'views/product_template_view.xml',
        #'report/report_production_order_inherit.xml',
        'report/report_inherit_purchase_requisition.xml',
        # 'report/purchase_order_report.xml',
        "views/purchase_order.xml"
    ],
}
