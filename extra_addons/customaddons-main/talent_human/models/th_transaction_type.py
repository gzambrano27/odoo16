from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

TYPE = [('incomes','Incomes'),('expenses','Expenses')]
EXPENSE = [('discount','Discount'),('advance','Advance'),('loans','Loans'),('faltas','Faltas')]
INCOME = [('extra_hours','Extra Hours'),('other','Other Income')]
class ThTransactionType(models.Model):
    _name = 'th.transaction.type'
    _description = 'Transaction Type'

    code = fields.Char('code', size=64)
    name = fields.Char('Description', size=64)
    debit_account_id = fields.Many2one('account.account', 'Debit Account', store = True)
    credit_account_id = fields.Many2one('account.account', 'Credit Account', store = True)
    type = fields.Selection(TYPE,'type', default = 'incomes')
    type_expense = fields.Selection(EXPENSE,'type Expense', default = 'discount')
    type_income = fields.Selection(INCOME,'type Income', default = 'other')
    generate_lines_employee = fields.Boolean('Generate Lines of all employee',  help="If active this field, the discount generate lines for each employee. This discount are made monthly")
    value_extra = fields.Float('% value hours extra', digits=(16, 2))
    sum_calculate_iess = fields.Boolean('Suma en el cálculo del IESS')