{
    'name': 'Metodos de Reportes para XLSX',
    'version': '1.0',
    'category': 'Se agrega funciones complementarias para reportes en xls',
    'description': """

    """,
    'author': "GPS",
    'website': '',
    'depends': [
         'report_xlsx_helper','account_reports'

    ],
    'data': [
        'security/ir.model.access.csv',
        'reports/ir_actions_report_xml.xml',
        'wizard/security_group_wizard.xml',
        'views/account_report.xml',
        'views/account_report_line.xml',
        'views/ir_ui_menu.xml',
    ],
    'installable': True,
}
