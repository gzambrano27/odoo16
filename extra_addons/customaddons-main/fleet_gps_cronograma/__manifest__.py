{
    'name': 'Cronograma de Maniobras',
    'version': '16.0.1.0.0',
    'author': 'MATHEU ZAMBRANO',
    'category': 'Fleet',
    'summary': 'Calendario de maniobras con flujo de aprobación',
    'depends': ['fleet', 'mail'],
    'data': [
        'security/fleet_cronograma_groups.xml',
        'security/ir.model.access.csv',
        'security/fleet_cronograma_record_rules.xml',
        'data/sequences.xml',
        'data/tipo_tags.xml',
        'data/cron_send_pending.xml',
        'views/cronograma_print_wizard_views.xml',
        'views/fleet_cronograma_views.xml',
        'reports/cronograma_report_template.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'assets': {
        'web.report_assets_common': [
            'fleet_gps_cronograma/static/img/GPS_LOGO.png',
        ],
    },
    'controllers': [
        'controllers/fleet_cronograma_controller.py',
    ],
    'installable': True,
    'application': False,
}
