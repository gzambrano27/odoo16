# models/account_account.py'
from odoo import models, fields, api, _

class AccountAccount(models.Model):
    _inherit = 'account.account'

    nombre_cuenta_nuevo_plan = fields.Char(
        string="Nombre de la Cuenta (Nuevo Plan de Cuenta)")
    codigo_cuenta_contable_nuevo_plan = fields.Char(
        string="Código Cuenta Contable (Nuevo Plan de Cuenta)")
    codigo_supercia_id = fields.Many2one('account.account.supercias',string="Código Supercia")
    grupo_supercia = fields.Char(string="Grupo Supercia")
    cuenta_supercia = fields.Char(string="Cuenta Supercia")
    codigo_ir_mapeo = fields.Char(string="Código (Formulario IR Mapeo)")
    cuenta_servicio_rentas_internas = fields.Char(
        string="Cuenta Servicio de Rentas Internas (Mapeo)")

    @api.onchange('codigo_supercia_id')
    def _onchange_codigo_supercia(self):
        for rec in self:
            rec.grupo_supercia = rec.codigo_supercia_id.name or ''