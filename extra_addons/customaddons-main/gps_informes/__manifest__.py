{
    'name': 'Cambios en Reportes Financieros,..etc',
    'version': '1.0',
    'category': 'Se agrega campos complementarios para reportes financieros',
    'description': """

    """,
    'author': "GPS",
    'website': '',
    'depends': [
        'account_reports',
        'gps_edi_ec',
        'report_xlsx_helper',
        'gps_purchases',
        'gps_bancos'
    ],
    'data': [
        'security/ir.model.access.csv',
        'reports/ir_actions_report_xml.xml',
        'wizard/l10n_ec_account_report.xml',
        'views/ir_ui_menu.xml',

    ],
    'installable': True,
}
