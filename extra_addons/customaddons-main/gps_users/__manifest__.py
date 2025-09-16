
{
    'name': 'Usuarios',
    'version': '1.0',
    'category': 'Se realzia las validaciones para usuarios y partners',
    'description': """

    """,
    'author': "GPS",
    'website': '',
    'depends': [
         'hide_any_menu'
    ],
    'data': [
        'data/ir_config_parameter.xml',
        'security/res_groups.xml',
        'views/res_groups.xml',
        'views/res_partner.xml',

    ],
    'installable': True,
}
