# -*- coding: utf-8 -*-
{
    "name": "Postventa - Requerimiento de Servicio",
    "version": "16.0.1.0.0",
    "author": "MATHEU ZAMBRANO",
    "category": "Services",
    "summary": "Módulo para gestionar requerimientos de servicio postventa",
    "depends": [
        "base",
        "mail",
        "contacts",
        "analytic",
    ],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/postventa_request_views.xml",
    ],
    'images': ['static/description/icono.png'],

    'icon': 'postventagps/static/description/icono.png',
    "installable": True,
    "application": False,
    "auto_install": False,
}
