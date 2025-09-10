from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

SCHEDULE_PAYMENTS = [('monthly', 'Monthly'), ('biweekly', 'Biweekly'), ('Weekly', 'Weekly')]
FIRST_FITTEN_PAYMENT_MODE = [('percent', 'Percent'), ('amount', 'Amount')]

class HrContract(models.Model):
    _inherit = 'hr.contract'
    #horario
    working_hours = fields.Many2one('resource.calendar', string='Working Hours', required=True)
    #area
    department_id = fields.Many2one('hr.department', string='Department', required=True,tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company,tracking=True)
    #cargo
    job_id = fields.Many2one('hr.job', string='Job Position', required=True)
    sectorial_table_id = fields.Many2one('th.sectorial.commission.table', string='Sectorial Table')
    line_historic_ids = fields.One2many('th.contract.historic', 'contract_id', string='Historic Lines')
    contract_income_ids = fields.One2many('th.contract.income', 'contract_id', string='Income Lines')
    contract_expense_ids = fields.One2many('th.contract.expense', 'contract_id', string='Expense Lines')
    pay_reserve_funds = fields.Boolean('Pay Reserve Funds', default=True,tracking=True)
    pay_thirteenth_salary = fields.Boolean('Pay Thirteenth Salary', default=True,tracking=True)
    pay_fourteenth_salary = fields.Boolean('Pay Fourteenth Salary', default=True,tracking=True)
    add_iees = fields.Boolean('Add IESS', default=True,tracking=True)
    add_judicial_reten = fields.Boolean('Add Judicial Retention', default=True)
    aditional_hold = fields.Boolean('Retencion', help="activa esta casilla si el empleado tiene retenciones")
    number_of_payments = fields.Integer('Number of Payments', default=12)
    active_contract = fields.Boolean('Active Contract', default=True)
    wage_history = fields.Float('Wage History', digits=(16, 2))
    schedule_pay = fields.Selection(SCHEDULE_PAYMENTS, string='Schedule Payments', default='2',tracking=True)
    first_fitten_payment_mode = fields.Selection(FIRST_FITTEN_PAYMENT_MODE, string='First Fitten Payment Mode', default='percent',tracking=True)
    value = fields.Float('Value', digits=(16, 2), default=50.0,tracking=True)
    salary_rule_ids = fields.Many2many('hr.salary.rule', string='Salary Rules')
    provincia_inicio = fields.Many2one('res.country.state', string='Provincia Inicio', required=True,tracking=True)
    ciudad_inicio = fields.Char('Ciudad Inicio', required=True)
    provincia_fin = fields.Many2one('res.country.state', string='Provincia Fin')
    gastos_lines = fields.One2many('th.record.expense.deducible', 'contrato_id', string='Gastos Lines')
    fifty_percent_hour = fields.Float('Fifty Percent Hour', digits=(16, 2),tracking=True)
    one_hundred_percent_hour = fields.Float('One Hundred Percent Hour', digits=(16, 2),tracking=True)


class ThContractHistoric(models.Model):
    _name = "th.contract.historic"
    _description = "Historical contract of employee"

    contract_id = fields.Many2one('hr.contract', string='Contract', ondelete="cascade")
    name = fields.Datetime(string='Date', required=True)
    wage = fields.Float(digits=(16, 2), string='Wage')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)

class ThContractIncome(models.Model):
    _name = 'th.contract.income'
    
    name = fields.Many2one('th.transaction.type', string='Name', required=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', ondelete="cascade")
    amount = fields.Float('Amount', digits=(16, 2))
    collection_form = fields.Selection([('middle_month', 'Middle of the month'), ('end_month', 'End of the month'), ('middle_end_month', 'Middle and End of the month')], 'Collection Form', default='end_month')

class ThContractExpense(models.Model):
    _name = 'th.contract.expense'
    
    name = fields.Many2one('th.transaction.type', string='Name', required=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', ondelete="cascade")
    amount = fields.Float('Amount', digits=(16, 2))
    collection_form = fields.Selection([('middle_month', 'Middle of the month'), ('end_month', 'End of the month'), ('middle_end_month', 'Middle and End of the month')], 'Collection Form', default='end_month')
