# -*- coding: utf-8 -*-
{
    "name": "PR State Traceability",
    "summary": "Guarda la trazabilidad de cambios de estado en Requisiciones de Compra (quién y cuándo).",
    "version": "16.0.1.0.0",
    "category": "Purchases Requisitions",
    "author": "Washington Guijarro",
    "license": "LGPL-3",
    "depends": ["purchase", "mail", 'purchase_request'],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "views/purchase_request_state_log_views.xml",
        "views/purchase_request_views.xml"
    ],
    "installable": True,
    "application": False
}
