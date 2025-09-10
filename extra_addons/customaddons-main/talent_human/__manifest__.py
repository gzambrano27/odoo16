# -*- coding: utf-8 -*-
{
    'name': "talent_human",

    'summary': """
        talen human for ecuadoria location""",

    'description': """
        talent human module for ecuadoria location and iess rules, included ISR rules and other rules 
    """,

    'author': "forestdbs",
    'website': "https://www.forestdbs.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ["hr_contract","hr_payroll","hr_payroll_account","hr_holidays","hr_attendance","hr","account"],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/th_transaction_type.xml',
        'views/th_sectorial_commission.xml',
        'views/hr_employee.xml',
        'views/hr_contract.xml',
        'wizard/th_advance_by_employees.xml',
        'views/th_discount.xml',
        'views/th_discount_run.xml',
        'views_sql/view_employee_contract_info.xml',
        ####
        'views/hr_gastos_deducibles.xml',
        
        ####
        'views/menu_items.xml',
        
    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
    'installable': True,
    'application': True,
    
    'assets': {
        'web.assets_backend': [
            'talent_human/static/src/css/custom_styles.css',
        ],
    },
}
