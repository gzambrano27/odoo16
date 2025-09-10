from odoo import api, fields, models, tools, _


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'
    _order = 'category_id asc, sequence asc'
    
    is_provision = fields.Boolean('Is Provision')
    generate_move = fields.Boolean('Generate Move Account',  help="check this field if your rule generate lines move account in the move account", default = True)
    type_base_income = fields.Selection((('remuneration','Remuneration'),
                                       ('extra_hours','Extra hours'),
                                       ('comisions','Comisions'),
                                       ('fixed_income','Other fixed income'),
                                       ('not_applicable','Not applicable')),string='Type Base', default = 'not_applicable')
    nombre_reporte = fields.Char('Presentacion en Reporte')    
    


class hr_salary_rule_category(models.Model):
    _inherit = 'hr.salary.rule.category'

    account_id = fields.Many2one('account.account', 'Account', help="This field is to reconcile the accounts discount")
        
