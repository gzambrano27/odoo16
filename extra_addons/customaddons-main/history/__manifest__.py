 # -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
{
    'name': "Historial y Log de Modificaciones",
    'summary': "Historial y Log de Modificaciones",
    'description': """

* Crear Objeto para registrar Log de Cambios(estados)
* Crear Objeto para registrar Log de Modificaciones
* Crear Objeto para ver las modificaciones en un Objeto


       """,
    'version': '16.0.0.0.1',
    'category': 'Technical Settings',
    'license': 'LGPL-3',
    'author': "Lajonner Crespin & Dalemberg Crespin",
    'website': "",
    'contributors': [],
    'depends': ['base'],
    'data': [ 
        'data/ir_module_category.xml',
        'data/res_groups.xml',        
        "security/ir.model.access.csv",
        'views/workflow_history.xml',
        "views/log_history_values.xml",
        "views/log_history.xml",
        "views/ir_ui_menu.xml", 
    ],
    'images': [
      
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

