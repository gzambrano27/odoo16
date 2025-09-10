from odoo import api, fields, models


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    tipo_cuenta = fields.Selection([
        ('Corriente', 'Cuenta Corriente'),
        ('Ahorro', 'Cuenta de Ahorros'),
        ('Tarjeta', 'Tarjeta de Credito'),
        ('Virtual', 'Virtual'),
        ], 'Tipo de Cuenta', default='Ahorro')