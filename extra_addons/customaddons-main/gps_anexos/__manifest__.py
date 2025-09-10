{
    'name': 'GPS Anexos',
    'version': '16.0.1.0.0',
    'author': 'Lajonner Crespin',
    'category': 'Accounting',
    'depends': ['gps_ats','gps_reports'],
    'data': [
        #'security/security.xml',
        #'security/ir.model.access.csv',
        #'views/einvoice_analysis_view.xml',
        'report/account_report.xml',
        'views/account_report_line.xml',
        'views/account_report.xml'
    ],
    'installable': True,
    'application': False,
}
