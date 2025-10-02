from odoo import models, fields

class ResCountry(models.Model):
    _inherit = 'res.country'

    use_iban = fields.Boolean(string='Requiere IBAN')
    name_dscr_bank= fields.Char(string='Nombre Pais')
