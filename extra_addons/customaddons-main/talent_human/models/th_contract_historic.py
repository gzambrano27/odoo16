from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class ThContractHistoric(models.Model):
    _name = "th.contract.historic"
    _description = "Historical contract of employee"

    contract_id = fields.Many2one('hr.contract',string='Contract', ondelete="cascade")
    name = fields.Datetime(string='Date',  required=True)
    wage = fields.Float(digits=(16,2),string='wage')
    user_id = fields.Many2one('res.users', 'User',default = lambda self: self.env.user)      



# class th_contract_line(object):
#     name = fields.Many2one('hr.transaction.type', 'Name', required=True)
#     contract_id = fields.Many2one('hr.contract', 'contract', required=False, ondelete="cascade")
#     amount = fields.Float('amount', digits=(16,2))
#     collection_form = fields.Selection([('middle_month','Middle of the month'),('end_month','End of the month'),('middle_end_month','Middle and End of the month'),], 'Collection Form', default = 'end_month')
 
 
#class hr_contract_income(models.Model,hr_contract_line):
class ThContractIncome(models.Model):
    _name = 'th.contract.income'   
    #_columns=hr_contract_line.columns
    name = fields.Many2one('th.transaction.type', 'Name', required=True)
    contract_id = fields.Many2one('hr.contract', 'contract', required=False, ondelete="cascade")
    amount = fields.Float('amount', digits=(16,2))
    collection_form = fields.Selection([('middle_month','Middle of the month'),('end_month','End of the month'),('middle_end_month','Middle and End of the month'),], 'Collection Form', default = 'end_month')
 
 
#class hr_contract_expense(models.Model,hr_contract_line):
class ThContractExpense(models.Model):
    _name = 'th.contract.expense'
    #_columns=hr_contract_line.columns
    name = fields.Many2one('th.transaction.type', 'Name', required=True)
    contract_id = fields.Many2one('hr.contract', 'contract', required=False, ondelete="cascade")
    amount = fields.Float('amount', digits =(16,2))
    collection_form = fields.Selection([('middle_month','Middle of the month'),('end_month','End of the month'),('middle_end_month','Middle and End of the month'),], 'Collection Form', default = 'end_month')
