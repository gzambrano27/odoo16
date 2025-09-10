{
    'name': 'Importar Stock Valuation Layer desde Excel',
    'version': '16.0.1.0.0',
    'depends': ['stock'],
    'author': 'ChatGPT',
    'category': 'Inventory',
    'summary': 'Importa registros en stock.valuation.layer desde un archivo Excel',
    'data': [
        'security/ir.model.access.csv',
        'wizards/wizard_import_stock_valuation_view.xml',
    ],
    'installable': True,
    'application': False,
}