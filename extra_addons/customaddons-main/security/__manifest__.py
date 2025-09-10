 # -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
{
    'name': "Seguridad",
    'summary': "Seguridad",
    'description': """

* Permite Configurar los objetos que deseas registrar los cambios.


       """,
    'version': '16.0.0.0.1',
    'category': 'Technical Settings',
    'license': 'LGPL-3',
    'author': "Lajonner Crespin & Dalemberg Crespin",
    'website': "",
    'contributors': [],
    'depends': ['history'],
    'data': [
            'data/log_configuration_model.xml',
            'security/ir.model.access.csv',
            'views/log_configuration_model.xml',
            'views/ir_ui_menu.xml',
            
    ],
    'images': [
      
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

