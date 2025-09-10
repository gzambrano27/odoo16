# __manifest__.py
{
    'name': 'Extensión Account con Supercias',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Añade nuevos campos a account.account y crea modelo Grupo Supercia',
    'depends': ['account', 'base', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_account_supercias_views.xml',
        'views/account_account_views.xml',
    ],
    'installable': True,
    'application': False,
}
