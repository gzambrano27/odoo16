{
    'name': 'Cronograma Valorado',
    'version': '1.0',
    'summary': 'Gestión de planillas con rubros',
    'author': 'Guillermo Zambrano',
    'depends': ['base', 'hr', 'account','portal','stock'],  # Asegúrate de incluir las dependencias necesarias
    'data': [
        'data/sequences.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/planilla_views.xml',
        'views/menu_views.xml'
    ],
    'images': [  # Archivos de imagen relacionados con el módulo (como logotipos o íconos).
        'static/description/logo.png',  # Logo del módulo.
        'static/description/icon.png'  # Icono del módulo.
        'static/src/logo_gps.png'   # Icono del grafica.
    ],
    'installable': True,
    'application': True,
}
