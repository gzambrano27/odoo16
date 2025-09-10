{
    'name': 'Helpdesk Extension',
    'version': '1.0',
    'summary': 'Customize Helpdesk for Employees',
    'description': 'Restrict Helpdesk menu and views for employees to only show their tickets.',
    'author': 'Your Name',
    'depends': ['helpdesk'],
    'data': [
                'security/ir.model.access.csv',
                'security/ir.rule.xml',
                'views/helpdesk_ticket_views.xml',
    ],
    'installable': True,
    'application': False,
}