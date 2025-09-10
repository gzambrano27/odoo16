
{
    "name": "Power BI Dashboards",
    "version": "16.0.1.0.0",
    "category": "Reporting",
    "summary": "Visualización de informes Power BI desde Odoo",
    "depends": ["base"],
    "data": [
        'security/dashboard_groups.xml',
        'security/ir.model.access.csv',
        'views/dashboard_views.xml',
        'views/dashboard_menus.xml',
        #'security/dashboard_group_rule.xml',
    ],
    'images': [  # Archivos de imagen relacionados con el módulo (como logotipos o íconos).
        'static/description/icon.png'  # Icono del módulo.
    ],
    "installable": True,
    "application": True
}
