{
    'name': 'Planillas',
    'version': '1.0',
    'summary': 'Gestión de planillas con secciones, categorías y rubros',
    'author': 'Guillermo Zambrano',
    'depends': ['base', 'hr', 'account','portal','stock'],  # Asegúrate de incluir las dependencias necesarias
    'data': [
        'data/sequences.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/seccion_views.xml',
        'views/categoria_views.xml',
        'views/rubro_views.xml',
        'views/planilla_views.xml',
        'views/menu_views.xml'

    ],
    'images': [  # Archivos de imagen relacionados con el módulo (como logotipos o íconos).
        'static/description/logo.png',  # Logo del módulo.
        'static/description/icon.png'  # Icono del módulo.
    ],
    'installable': True,
    'application': True,
}
