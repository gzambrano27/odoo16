{
    'name': 'Cambios en CRM',
    'version': '1.0',
    'category': 'Se agrega campo de proyecto en oportunidad de CRM',
    'description': """

    """,
    'author': "GPS",
    'website': '',
    'depends': [
         'sale_crm','account_payment_purchase','crm'
    ],
    'data': [
        "security/ir.model.access.csv",
        'security/crm_lead_groups.xml',
        'security/crm_lead_rules.xml',
        "data/ir_sequence.xml",
        "data/scoring_template_demo.xml",
        "views/crm_correos.xml",
        "views/crm_lead_project.xml",
        "views/crm_lead.xml",
        "views/sale_order.xml",
        "views/rangos_configuracion_view.xml",
        "views/ir_ui_menu.xml",
        "views/crm_lead_views.xml",
    ],
    'installable': True,
}
