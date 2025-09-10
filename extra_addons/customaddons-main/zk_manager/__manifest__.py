# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'ZKteco Manager',
    'version': '16.0.0.0.1',
    'category': 'ZKteco',
    'license': 'LGPL-3',
    'author': "Lajonner Crespín & Dalemberg Crespín",
    'summary': "ZKteco Manager",
    'description': """* Control de dispositivos ZKTeco

       """,
    'website': None,
    'depends': ['hr_zk_attendance'],

    'data': [
        "data/ir_config_parameter.xml",

        "security/ir.model.access.csv",

        "wizard/zk_machine_wizard.xml",

        "views/zk_machine.xml",
    ],
    'demo': [

    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'qweb': [

    ],
}
