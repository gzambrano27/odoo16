
{
    'name': 'Cambios en Nomina',
    'version': '1.0',
    'category': 'Se realiza  cambios de nomina',
    'description': """

    """,
    'author': "GPS",
    'website': '',
    'depends': [
         'maintenance_add_actas','talent_human','fx','hr_employee_relative',
        'gps_reports','base_cash_management','gps_payment','gps_users','gps_actas','sde_document'
    ],
    'data': [        

        "security/ir_module_category.xml",
        "security/res_groups.xml",

        "security/ir.model.access.csv",

        "sql/CROSSTAB.sql",

        "data/dynamic_function.xml",
        "data/hr_salary_rule_category.xml",
        "data/hr_salary_rule.xml",

        "data/ir_config_parameter.xml",

        "data/hr_work_entry_type.xml",

        "data/ir_cron.xml",

        "mail/mail_template.xml",


        "security/ir_rule.xml",

        "wizard/hr_employee_movement_wizard.xml",
        "wizard/hr_payslip_employees.xml",
        "wizard/hr_employee_payslip_reports_wizard.xml",
        "wizard/hr_employee_report_wizard.xml",
        "wizard/hr_employee_proyeccion_wizard.xml",
        "wizard/hr_vacation_period_wizard.xml",

        "wizard/hr_vacation_period_line_wizard.xml",

        'wizard/hr_payslip_payment_wizard.xml',

        'wizard/hr_employee_update_request_wizard.xml',

        "reports/hr_payslip.xml",
        "reports/ir_actions_report_xml.xml",

        "views/hr_salary_rule_account.xml",
        "views/hr_department.xml",
        "views/res_partner_bank.xml",

        "views/hr_salary_rule_category.xml",
        "views/hr_salary_rule.xml",
        "views/hr_payroll_structure.xml",
        "views/hr_employee_movement_line.xml",
        "views/hr_employee_movement.xml",

        "views/hr_mail_message.xml",
        "views/hr_employee.xml",

        "views/hr_payslip_run.xml",
        "views/hr_payslip.xml",
        "views/hr_payslip_input.xml",

        "views/hr_contract_type.xml",

        "views/hr_payslip_move.xml",

        "views/res_company.xml",

        "views/hr_contract.xml",

        "views/th_family_burden.xml",
        "views/hr_employee_relative.xml",

        "views/hr_employee_payment.xml",

        "views/hr_payroll_structure_type.xml",

        "views/hr_deductible_expenses_period.xml",

        "views/hr_employee_historic_lines.xml",

        'views/hr_deductible_expenses_contract_period_template.xml',

        "views/hr_employee_liquidation.xml",
        "views/hr_vacation_period.xml",

        "views/hr_vacation_period_line.xml",

        'views/res_bank_code.xml',

        "views/hr_leave_type.xml",

        "views/hr_leave.xml",

        "views/hr_employee_update_request.xml",

        "views/hr_payslip_view.xml",
        'views/maintenance_acta_view.xml',

        "views/actas_acta.xml",
        "views/hr_employee_view.xml",

        "views/ir_ui_menu.xml",
    ],
    'installable': True,
}
