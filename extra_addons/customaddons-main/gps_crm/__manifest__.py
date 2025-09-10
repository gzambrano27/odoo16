{
    'name': 'Cambios en CRM',
    'version': '1.0',
    'category': 'Se agrega campo de proyecto en oportunidad de CRM',
    'description': """

    """,
    'author': "GPS",
    'website': '',
    'depends': [
         'sale_crm'
    ],
    'data': [
        "security/ir.model.access.csv",
        "views/crm_correos.xml",
        "views/crm_lead_project.xml",
        "views/crm_lead.xml",
        "views/sale_order.xml",
         "views/ir_ui_menu.xml",
    ],
    'installable': True,
}
