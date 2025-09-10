
{
    'name': 'Cuentas Analiticas',
    'version': '1.0',
    'category': 'Se realiza  cambios en cuentas analiticas',
    'description': """

    """,
    'author': "GPS",
    'website': '',
    'depends': [
         'gps_purchases','gps_informes','hr_timesheet'
    ],
    'data': [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "reports/ir_actions_report_xml.xml",
        "wizard/account_analytic_account_wizard.xml",
        "views/account_analytic_account.xml",
        'views/ir_ui_menu.xml'
    ],
    'installable': True,
}
