{
    'name': 'Cargar Saldos Iniciales',
    'version': '16.0.1.0',
    'summary': 'Importar asientos de saldos iniciales desde un archivo CSV.',
    'author': 'Tu Nombre',
    'depends': ['account'],
    'data': [
        "security/ir.model.access.csv",
        'wizard/load_initial.xml',
    ],
    'installable': True,
    'application': False,
}