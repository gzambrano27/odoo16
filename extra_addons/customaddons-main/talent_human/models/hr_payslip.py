from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class hr_payslip(models.Model):
    _inherit = 'hr.payslip'
    _order = 'employee_id asc'


    name = fields.Char('Description', size=256)
    total_of_hours = fields.Float(string='Total of hours')
    wk_days = fields.Float('Work Days', digits =(16,2))
    total_payslip_lines = fields.Float(string='Total of Payslip', digits =(16,2))
    leaves_days_line_ids = fields.One2many('hr.payslip.leaves_days', 'payslip_id', 'Payslip Leaves Days')
    discount_lines_ids = fields.One2many('th.payslip.discount', 'payslip_id', 'Payslip', required=False)
    #department_id = fields.Many2one ('department_id', related = 'contract_id',  relation="hr.department",string='Department',store=True)
    department_id = fields.Many2one ("hr.department",string='Department',store=True)
    payslip_run_id = fields.Many2one('hr.payslip.run', 'Payslip Batches', readonly=True,ondelete="cascade")
    total_discounts = fields.Float(string='Total Discounts')
    area = fields.Many2one('account.area', 'Area')
    rol_agricola = fields.Boolean('Rol Agricola')
    pago_archivo = fields.Boolean('Pago/Archivo',default = True)
    discontinuo = fields.Boolean('Discontinuo')
    rol_empaque = fields.Boolean('Rol Empaque')
    
    

class hr_payslip_line(models.Model):
    _inherit = 'hr.payslip.line'

    type_base_income = fields.Selection((('remuneration','Remuneration'),
                                       ('extra_hours','Extra hours'),
                                       ('comisions','Comisions'),
                                       ('fixed_income','Other fixed income'),
                                       ('not_applicable','Not applicable')),string='Type Base', default = 'not_applicable')
    is_provision = fields.Boolean('Is Provision')
    #payslip_run_id = fields.Many2one ('payslip_run_id',related = 'slip_id', relation="hr.payslip.run",string='Payslip Run',store=True)
    payslip_run_id = fields.Many2one ("hr.payslip.run",string='Payslip Run',store=True)
    #department_id = fields.Many2one ('department_id', related = 'slip_id', relation="hr.department",string='Department',store=True)
    department_id = fields.Many2one ("hr.department",string='Department',store=True)


class hr_payslip_discount(models.Model):
    _name = 'th.payslip.discount'
    
    name = fields.Char('Name', size=64)
    code = fields.Char('code',size=64)
    date = fields.Date('Date')
    amount = fields.Float('amount', digits = (16,2))
    number_quota = fields.Integer('Number Quota')
    payslip_id = fields.Many2one('hr.payslip', 'Payslip', ondelete="cascade")
    discount_line_id = fields.Many2one('th.discount.lines', 'Discount Line')
    expense_type_id = fields.Many2one('th.transaction.type', 'Expense Type')
    prestamo_id = fields.Many2one("hr.prestamos","Ingreso y Egresos")
    multa_id = fields.Many2one("hr.multas","Ingreso y Egresos")
    otros_dsctos_id = fields.Many2one("hr.otros.descuentos","Ingreso y Egresos")
    
    
    
    


class hr_payslip_leaves_days(models.Model):
    _name = 'hr.payslip.leaves_days'
    _inherit = 'hr.payslip.worked_days'

    transaction_id = fields.Many2one("th.transaction.type","Rubro")

    
        

class hr_payslip_input(models.Model):
    _inherit = 'hr.payslip.input'

    #income_type_id = fields.Many2one('th.transaction.type', 'Income Type')
    code = fields.Char('code', size=64,  help="The code that can be used in the salary rules")
    sum_calculate_iess = fields.Boolean('Suma en el cálculo del IESS', default = True)
    #prestamo_id = fields.Many2one("hr.prestamos","Ingreso y Egresos")

    

class hr_payslip_worked_days(models.Model):

    _inherit = 'hr.payslip.worked_days'

    transaction_id = fields.Many2one('hr.transaction.type', 'Type')
    percentage_extra = fields.Float('% value Hours Extra', digits = (16,2))
    sum_calculate_iess = fields.Boolean('Suma en el cálculo del IESS', default = True)