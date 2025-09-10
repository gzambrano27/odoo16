from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError



BONUS_REPOSITION_TYPE = [("BONUS","INGRESO ABONO")]
class ThEmployeeBonus(models.Model):
    _name = 'th.employee.bonus'
    _description = 'Employee Bonus'


    name = fields.Many2one('th.transaction.type', string='Name', readonly=True)
    type = fields.Selection(BONUS_REPOSITION_TYPE, string='Type', required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, readonly=True)
    ref = fields.Char(string='Reference', required=True)
    partner_id = fields.Many2one("res.partner", string="Partner Employee", store=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    move_id = fields.Many2one('account.move', string='Move', readonly=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, readonly=True)
    date = fields.Date(string='Date', required=True)
    date_from = fields.Date(string='Due Date', required=True)
    amount = fields.Float(string='Amount', required=True)
    paid = fields.Boolean(string='Paid', default=False)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    state = fields.Selection([ ('draft', 'Draft'), ('posted', 'Posted'), ('cancel', 'Cancelled')], string='State', default='draft', readonly=True)
    
    observation = fields.Text(string='Observation')
    discount_ids = fields.One2many('th.discount.lines', 'bonus_id', string='Discounts')
    total = fields.Monetary(string='Total')
    paid_value = fields.Monetary(string='Paid Value')
    residual = fields.Monetary(string='Residual')
    credit_account_id = fields.Many2one('account.account', string='Credit Account', required=True)

    
