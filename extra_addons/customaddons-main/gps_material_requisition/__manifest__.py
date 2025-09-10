# -*- coding: utf-8 -*-
{
    'name': "Importar y Exportar Requisicion de Materiales",

    'summary': """
        Se agrega nuevas funcionalidad para descargar e importar Requisicion de Materiales""",

    'description': """
        Cambios en requisicion de materiales
    """,

    'author': "Washington Guijarro",
    'website': "https://gpsgroup.com.ec",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Requisition Purchase Material',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'material_purchase_requisitions','account_payment_purchase'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/material_requisition_wizard.xml',
        'views/purchase_requisition_view.xml',
        'report/orden_trabajo.xml',
    ],
}
