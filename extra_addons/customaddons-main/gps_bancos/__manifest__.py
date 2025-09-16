{
    'name': 'Cambios para Documentos Bancarios,etc...',
    'version': '1.0',
    'category': 'Cambios para Documentos Bancarios,etc...',
    'description': """

    """,
    'author': "GPS",
    'website': '',
    'depends': [
         'gps_edi_ec','report_xlsx_helper','gps_hr','gps_purchases','gps_payment'
    ],
    'data': [

        'data/ir_config_parameter.xml',
        'data/ir_sequence.xml',
        'data/ir_cron.xml',



        'mail/mail_account_move.xml',
        'mail/mail_account_payment_request.xml',
        'mail/mail_purchase_order.xml',
        'mail/mail_template_pago_banco.xml',
        'mail/mail_account_payment.xml',
        'mail/mail_template_alarma_pago.xml',

        'security/ir_module_category.xml',
        'security/res_groups.xml',
        'security/ir.model.access.csv',

        'security/ir_model_access.sql',

        'data/ir_actions_server.xml',
        'data/account_group_report.xml',
        'data/account_payment_request_type.xml',

        'data/document_bank_reconciliation_type.xml',

        'data/res_partner_category.xml',

        'reports/report_paperformat.xml',
        'reports/account_payment_bank_macro.xml',

        'reports/document_financial_line_report_handler_supplier.xml',
        'reports/document_financial_line_report_handler_customer.xml',
        'reports/document_financial_line_report_handler.xml',

        'reports/account_payment_bank_macro_summary.xml',

        'reports/res_partner.xml',

        'reports/ir_actions_report_xml.xml',



        'wizard/document_financial_wizard.xml',
        'wizard/account_payment_request_wizard.xml',

        'wizard/account_payment_reports_wizard.xml',
        'wizard/res_partner_bank_wizard.xml',
        'wizard/account_payment_request_workflow_wizard.xml',
        'wizard/account_payment_analysis_request_selection_wizard.xml',

        'wizard/document_financial_version_wizard.xml',
        'wizard/document_financial_liquidation_version_wizard.xml',
        'wizard/update_reconciliation_type_wizard.xml',

        'wizard/account_payment_register.xml',


        'wizard/res_partner_bank_email_update_wizard.xml',

        'wizard/account_payment_multicompany.xml',

        'views/document_financial_version.xml',

        'views/account_payment_analysis_request_wizard.xml',

        'views/account_move.xml',
        'views/account_move_line.xml',

        'views/document_financial_line.xml',
        'views/document_financial.xml',
        'views/document_financial_line_payment.xml',
        'views/document_financial_line_payment_group.xml',

        'views/res_bank.xml',
        'views/account_configuration_payment.xml',
        'views/purchase_order.xml',

        'views/account_payment_request_type.xml',
        'views/account_payment.xml',
        'views/account_payment_request.xml',
        'views/account_payment_bank_macro.xml',
        'views/account_payment_bank_macro_line.xml',
        'views/account_payment_bank_macro_summary.xml',

        'views/res_partner_bank.xml',
        'views/res_partner.xml',

        'views/account_group_report.xml',
        'views/account_partner_group_category.xml',

        'views/bank_mail_message.xml',
        'views/account_payment_term.xml',
        'views/document_financial_placement.xml',
        'views/document_financial_liquidation.xml',
        'views/document_bank_reconciliation.xml',
        'views/document_bank_reconciliation_line.xml',
        'views/document_bank_reconciliation_line_group.xml',

        'views/document_bank_reconciliation_type.xml',
        'views/hr_employee_payment.xml',
        'views/hr_salary_rule.xml',

        'views/hr_employee_liquidation.xml',

        'views/bank_account_template.xml',

        'views/res_partner_bank_request.xml',

        'views/ir_ui_menu.xml',
    ],
    'installable': True,
}
