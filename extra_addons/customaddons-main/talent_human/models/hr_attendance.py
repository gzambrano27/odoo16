from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class Thattendance(models.Model):
    _inherit = 'hr.attendance'

    check_in_break = fields.Datetime(string="Check In Sist")
    check_out_break = fields.Datetime(string="Check Out Sist")
    codigoproceso  = fields.Char('Proceso')
    codigoprocesoact = fields.Char('Proceso Actualiza')

    