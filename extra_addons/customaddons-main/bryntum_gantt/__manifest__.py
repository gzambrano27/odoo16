{
    "name": "Gantt View PRO",
    "summary": """
    Manage and visualise your projects with the fastest Gantt chart on the web.
    """,
    "author": "Bryntum AB",
    "website": "https://www.bryntum.com/forum/viewforum.php?f=58",
    # Categories can be used to filter modules in modules listing
    # for the full list
    "category": "Project",
    "version": "16.0.2.1.21",
    "price": 890.00,
    "currency": "EUR",
    "license": "Other proprietary",
    "support": "odoosupport@bryntum.com",
    "live_test_url": "https://odoo-gantt16ce.bryntum.com",
    # any module necessary for this one to work correctly
    "depends": ["base", "web", "project", "hr", "hr_timesheet"],
    "images": [
        "images/banner.png",
        "images/main_screenshot.png",
        "images/reschedule.gif",
    ],
    # always loaded
    "data": [
        "security/project_security.xml",
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/project_views.xml",
        "wizard/import_mpp_views.xml",
    ],
    "application": True,
    # only loaded in demonstration mode
    "demo": [
        "demo/demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "/bryntum_gantt/static/src/js/error_service.esm.js",
            "/bryntum_gantt/static/src/js/main.js",
            "/bryntum_gantt/static/src/css/main.css",
        ]
    },
    "post_init_hook": "post_init_hook",
}
