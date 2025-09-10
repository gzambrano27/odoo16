# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Funciones Dinámicas',
    'version': '16.0.0.0.1',
    'category': 'Technical Settings',
    'license': 'LGPL-3',
    'author': "Lajonner Crespin & Dalemberg Crespin",
    'summary': "Funciones Dinámicas",
    'description': """* Crear funciones dinámicas con código python
* Probar las funciones dinámicas

       """,
    'website': None,
    'depends': ['message_dialog','calendar_days','security'],

    'data': [
            "data/log_configuration_model.xml",
            "data/dynamic_function_property.xml",
            "data/dynamic_function.xml",
            "data/ir_module_category.xml",
            "data/res_groups.xml",            
            "wizard/dynamic_function_test_wizard.xml",
            "views/dynamic_function_interface.xml",
            "views/dynamic_function_property.xml",
            "views/dynamic_function.xml",
            "views/ir_ui_menu.xml",
            "security/ir.model.access.csv"
           ],
    'demo': [

    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'qweb': [
    
    ],
}