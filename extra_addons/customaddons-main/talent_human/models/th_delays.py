from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class ThDelays (models.Model):
    _name = 'th.delays'
    _description = 'Delays'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    date = fields.Date(string='Date', required=True)
    delay_hours = fields.Float(string='Delay Hours', required=True)
    delay_minutes = fields.Float(string='Delay Minutes', required=True)
    delay_seconds = fields.Float(string='Delay Seconds', required=True)
