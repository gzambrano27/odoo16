# -*- coding: utf-8 -*-
{
    "name": "Gestión de Ausencias",
    "version": "16.0.1.0.0",
    "category": "Human Resources",
    "summary": "Gestión de permisos y ausencias del personal",
    "description": """
Módulo para gestionar ausencias de empleados:
- Registro de solicitudes de ausencias
- Relación con contratos activos
- Detalle de periodos de vacaciones
- Subdetalles mensuales
- Control por grupos de permisos
    """,
    "author": "GPS GROUP",
    "website": "https://www.gpsgroup.com.ec",
    "license": "AGPL-3",
    "depends": [
        "base",
        "hr",
        "hr_contract",
        "mail"
    ],
    "data": [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "views/hr_absence.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
