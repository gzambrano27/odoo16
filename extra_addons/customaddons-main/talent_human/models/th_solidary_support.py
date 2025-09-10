from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

SUPPORT_TYPE = [("SUPPORT", "SUPPORT"), ("REPOSITION", "REPOSITION")]
class ThSolidarySupport(models.Model):
    _name = 'th.solidary.support'
    _description = 'Solidary Support'

    name = fields.Many2one('th.transaction.type', string='Name', readonly=True)
    type = fields.Selection(SUPPORT_TYPE, string='Type', required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, readonly=True)
    ref = fields.Char(string='Reference', required=True)
    partner_id = fields.Many2one("res.partner", string="Partner Employee", store=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    employee_paid = fields.Many2one('hr.employee', string='Employee Paid', required=True)
    partner_paid = fields.Many2one("res.partner", string="Partner Paid", store=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    date = fields.Date(string='Date', required=True)
    date_from = fields.Date(string='Due Date', required=True)
    amount = fields.Float(string='Amount', required=True)
    paid = fields.Boolean(string='Paid', default=False)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted'), ('cancel', 'Cancelled')], string='State', default='draft', readonly=True)
    observation = fields.Text(string='Observation')
    # payment_ids = fields.One2many('account.payment', 'support_id', string='Payments')
    has_payment = fields.Boolean(string='Has Payment', default=False)
    csv_export_file = fields.Binary(string='CSV Export File')
    csv_export_filename = fields.Char(string='CSV Export Filename')
