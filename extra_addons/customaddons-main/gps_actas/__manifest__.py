{
    'name': 'Actas',
    'version': '16.0.1.0',
    'summary': 'Gestión de Actas GPS',
    'author': 'Matheu Zambrano',
    'depends': ['hr', 'base', 'report_xlsx'],
    'data': [
        'security/actas_security.xml',
        'security/ir.model.access.csv',
        'reports/actas_template.xml',
        'data/actas_sequence.xml',
        'views/actas_view.xml',
        

    ],
    
    'images': [
        'static/src/img/GPS_LOGO.png',
        'static/src/img/icon.png',
    ],  # Ruta a la imagen del logo
    'installable': True,
    'auto_install': False,
    'application': True,
}