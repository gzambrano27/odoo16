from odoo.tools.translate import _
from odoo import api, fields, models, tools, netsvc, _


class res_company(models.Model):
    _inherit = 'res.company'

    schedule_pay = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('bi-monthly', 'Bi-monthly'),
        ('monthly', 'Monthly'),
        ], 'Scheduled Pay',default = 'monthly')
    property_account_payroll_employee = fields.Many2one('account.account', string="Cuenta de Pago de Empleados",method=True)
    fecha_reg_min_ausencia = fields.Datetime('F. Min Reg Ausencia')
    fecha_reg_ausencia = fields.Datetime('F. Max Reg Ausencia')
    asientos_tot_rrhh = fields.Boolean('Asientos Totalizados RRHH?')
