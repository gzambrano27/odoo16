from odoo import fields, models

class MeetingRoom(models.Model):
    _name = 'meeting.room'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Meeting Room'

    name = fields.Char(string='Nombre', required=True)
    location = fields.Char(string='Ubicación')
    manager_id = fields.Many2one('hr.employee', string='Responsable')
    capacity_min = fields.Integer(string='Capacidad mínima')
    capacity_max = fields.Integer(string='Capacidad máxima')
