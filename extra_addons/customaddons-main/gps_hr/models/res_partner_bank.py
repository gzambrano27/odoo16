# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from odoo.exceptions import ValidationError,UserError
from odoo import api, fields, models, _


class ResPartnerBank(models.Model):
    _inherit="res.partner.bank"

    tercero = fields.Boolean("Tercero",default=False)
    identificacion_tercero = fields.Char("# Identificacion Tercero")
    nombre_tercero = fields.Char("Nombre de Cuenta Tercero")
    l10n_latam_identification_tercero_id = fields.Many2one("l10n_latam.identification.type",
                                                           "Tipo de Identificacion Tercero")

    @api.onchange('tercero','partner_id','nombre_tercero')
    def onchange_nombre_tercero(self):
        if not self.tercero:
            self.acc_holder_name=self.partner_id.name
        else:
            self.acc_holder_name = self.nombre_tercero

    _sql_constraints = [
        ('unique_number', 'unique(sanitized_acc_number, partner_id, company_id)',
         'The combination Account Number/Partner/Company must be unique.')
    ]

    @api.constrains('sanitized_acc_number', 'partner_id', 'active')
    def _check_unique_account_partner_active(self):
        for rec in self:
            if not rec.active:
                # No validar si el registro está inactivo
                continue
            if rec.sanitized_acc_number and rec.partner_id:
                dup = self.search([
                    ('id', '!=', rec.id),
                    ('sanitized_acc_number', '=', rec.sanitized_acc_number),
                    ('partner_id', '=', rec.partner_id.id),
                    ('active', '=', True),  # solo activos
                ], limit=1)
                if dup:
                    raise ValidationError(_(
                        "El proveedor %s ya tiene registrada la cuenta %s. "
                        "Proceda a inactivar las cuentas previamente ingresadas con el mismo número."
                    ) % (rec.partner_id.display_name, rec.sanitized_acc_number))
