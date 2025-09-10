# -*- coding: utf-8 -*-
{
    'name': 'Control de Calidad - Reporte de Fallas',
    'version': '1.0.0',
    'summary': 'Módulo para administrar reportes de fallas y garantías.',
    'author': 'GPS Group',
    'website': 'http://www.gpsgroup.ec',
    'license': 'LGPL-3',
    'category': 'Quality',
    'depends': [
        'base',
        'analytic',  # Para usar account.analytic.account
        'web',
        'portal',
		'purchase_request'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'report/quality_control_report_templates.xml',
        'views/quality_control_views.xml',
        'views/menu_item_views.xml',
    ],
    'installable': True,
    'application': True,
}