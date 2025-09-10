{
    "name": "GPS Customization Copy",
    "version": "16.0.1.0.1",
    "category": "Uncategorized",
    "summary": "Custom Copys from NexGen to GPSGROUP",
    "license": "AGPL-3",
    "author": "Washington Guijarro",
    "installable": True,
    "auto_install": False,
    "depends": ["base","purchase"],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'wizard/purchase_order_copy_wiz.xml',
    ],
    'installable': True,
    'application': False,
}