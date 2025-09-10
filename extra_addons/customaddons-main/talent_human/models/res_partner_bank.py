
from odoo import api, fields, models, _
class res_partner_bank(models.Model):
    _inherit = 'res.partner.bank'
    
    is_default = fields.Boolean('Por defecto')
    