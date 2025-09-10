{
    'name': 'Cambios en Reportes Tributarios ATS,103,104,..etc',
    'version': '1.0',
    'category': 'Se agrega campos complementarios para reportes Tributarios',
    'description': """

    """,
    'author': "GPS",
    'website': '',
    'depends': [
         'gps_edi_ec','report_xlsx_helper'
    ],
    'data': [
        'security/ir.model.access.csv',
        'reports/ir_actions_report_xml.xml',
        'wizard/l10n_ec_ats.xml',
        'views/ir_ui_menu.xml',

    ],
    'installable': True,
}
