# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
{
    'name': "Maestros de Fecha",
    'summary': """

Agrega datos maestros para los calendarios

* Días de la Semana
* Días Feriados
* Mes del Año

    """,
    'version': '16.0.0.0.1',
    'category': 'Technical Settings',
    'license': 'LGPL-3',
    'author': "Lajonner Crespin & Dalemberg Crespin",
    'website': "",
    'contributors': [
            
    ],
    'depends': ['base'],
    'data': [ 
        "security/ir.model.access.csv",
        "data/calendar_day.xml",
        "data/calendar_month.xml",
        "data/calendar_holiday.xml",
        "views/calendar_day.xml",
        "views/calendar_month.xml",
        "views/calendar_holiday.xml",
        "views/calendar_legal_holiday.xml",
    ],
    'images': [
    
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

