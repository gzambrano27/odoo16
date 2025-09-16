# -*- coding: utf-8 -*-
{
    "name": "PR ↔ PO Analítico (Wizard)",
    "version": "16.0.1.0.0",
    "summary": "Reporte analítico PR ↔ PO con navegación a trazabilidad",
    "author": "GPS Group",
    "website": "",
    "license": "AGPL-3",
    "category": "Purchases/Reporting",
    "depends": ["base", "purchase", "analytic", "purchase_request"],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "views/pr_po_analytic_report_views.xml",
    ],
    "installable": True,
}