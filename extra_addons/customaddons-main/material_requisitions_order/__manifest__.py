# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': 'Ordenes de trabajo de Ingenieria',
    'version': '9.7.8',
    'price': 79.0,
    'currency': 'USD',
    'license': 'Other proprietary',
    'summary': "Product / Work Order and Stock Request by User",
    'description': "Work Orders",
    'author': 'GPS Group',
    'website': 'https://gpsgroup.com.ec',
    'support': 'gzambrano@gpsgroup.com.ec',
    'images': ['static/description/img1.jpeg'],
    #'live_test_url': 'https://youtu.be/1AgKs7gfe4M',
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/material_requisitions_order/304',#'https://youtu.be/byR2cM0c274',
    'category': 'Inventory/Inventory',
    'depends': [
                'stock',
                'hr',
                'purchase',
                'base'
                ],
    'data':[
        'security/security.xml',
        'security/multi_company_security.xml',
        'security/ir.model.access.csv',
        'data/purchase_requisition_sequence.xml',
        'data/employee_purchase_approval_template.xml',
        'data/confirm_template_material_purchase.xml',
        'report/purchase_requisition_report.xml',
        'wizard/material_requisition_wizard.xml',
        'views/purchase_requisition_view.xml',
        'views/work_order_view.xml',
    ],
    'installable' : True,
    'application' : False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
