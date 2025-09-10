{
    'name': 'Módulo Seguridad Física',
    'version': '1.0',
    'summary': 'Gestión de personal contratista, solicitudes, pruebas doping y envío a lista negra',
    'description': """
        Módulo para la seguridad física que incluye:
          - Registro de personal contratista.
          - Lista de solicitud con líneas de personas que aprueban el proceso de seguridad.
          - Envío a lista negra (modelo permisos_ingreso.lista_negra) validando que no exista ya.
          - Creación de registros en pruebas doping agrupados por fecha de doping.
          - Creación de personal para permiso en permisos_ingreso.personal, para los aprobados en doping.
    """,
    'category': 'Security',
    'author': 'Guillermo Zambrano',
	'website': 'https://www.gpsgroup.ec',
    'depends': ['base','permisos_ingreso'],
    'data': [
        'data/secuencia_security.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/personal_contratista_views.xml',
        'views/lista_solicitud_views.xml',
        'views/pruebas_doping_views.xml',
        'views/menu_views.xml',
    ],
    'images': ['static/src/img/logo.png'],
    'installable': True,
    'application': True,
}
