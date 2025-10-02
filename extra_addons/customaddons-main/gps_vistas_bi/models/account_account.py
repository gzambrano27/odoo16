from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Accountaccount(models.Model):
    _inherit = 'account.account'

    empresa_relacionada_id=fields.Many2one("res.partner",string="Empresa Relacionada")