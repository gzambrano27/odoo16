# -*- coding: utf-8 -*-
{
    "name": "PO State Traceability",
    "summary": "Guarda la trazabilidad de cambios de estado en Órdenes de Compra (quién y cuándo).",
    "version": "16.0.1.0.0",
    "category": "Purchases",
    "author": "Washington Guijarro",
    "license": "LGPL-3",
    "depends": ["purchase", "mail"],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "views/purchase_order_state_log_views.xml",
        "views/purchase_order_views.xml"
    ],
    "installable": True,
    "application": False
}
