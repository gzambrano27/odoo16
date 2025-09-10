from odoo import api, fields, models, _, Command
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError

class ApuApuTags(models.Model):
    _name = 'apu.apu.tags'
    _description = 'Etiquetas para APU'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True, translate=True)
    color = fields.Integer(string='Color')  # Odoo usa esto para el color visual de etiquetas