
{
    'name': 'Lectura y recuperacion de documentos del sri',
    'version': '1.0',
    'category': 'Lectura y recuperacion de documentos del sri',
    'description': """

    """,
    'author': "GPS",
    'website': '',
    'depends': [
         'l10n_ec'
    ],
    'data': [        

        "data/ir_cron.xml",
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "report/electronic_document_received_report.xml",
        "report/ir_actions_report_xml.xml",
        "wizard/electronic_document_received_workflow_wizard.xml",
        "views/electronic_document_received_batch.xml",
        "views/electronic_document_received.xml",
        "views/account_move.xml",
        "views/ir_ui_menu.xml",
    ],
    'installable': True,
}
