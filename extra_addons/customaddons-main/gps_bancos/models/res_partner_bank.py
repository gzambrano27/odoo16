# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID
import re

class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    full_name=fields.Char("# Cuenta",compute="_get_compute_full_name",store=False,readonly=True)
    partner_email=fields.Char("Correo")
    iban_number=fields.Char("# IBAN")
    active=fields.Boolean("Activo",default=True)

    def name_get(self):
        return [(acc.id,acc.full_name )
                for acc in self]

    def _get_compute_full_name(self):
        for brw_each in self:
            full_name="Cta %s # %s,%s" % (brw_each.tipo_cuenta,brw_each.acc_number or '',brw_each.bank_id and brw_each.bank_id.name or '')

            brw_each.full_name=full_name

    _rec_name="full_name"

    @api.constrains('iban_number', 'active')
    def _check_unique_iban(self):
        for record in self:
            if record.iban_number:
                # Buscar otros registros activos con el mismo IBAN
                other = self.search([
                    ('iban_number', '=', record.iban_number),
                    ('active', '=', True),
                    ('id', '!=', record.id)
                ])
                if other:
                    raise ValidationError(
                        f"El IBAN '{record.iban_number}' ya existe en otro registro activo."
                    )

    @api.onchange('tercero')
    def onchange_tercero(self):
        def get_identification_tipo_id(brw_parent):
            if brw_parent.country_id and brw_parent.country_id.code == 'EC':  # Verifica si el país es Ecuador
                if brw_parent.l10n_latam_identification_type_id == self.env.ref('l10n_ec.ec_ruc'):
                    return self.env.ref('l10n_ec.ec_dni')
            return False
        if not self.tercero:
            self.l10n_latam_identification_tercero_id=False
            self.identificacion_tercero=None
            self.nombre_tercero=None
        else:
            brw_parent=self.partner_id._origin
            identification_tipo_id=get_identification_tipo_id(brw_parent)
            if identification_tipo_id:
                self.l10n_latam_identification_tercero_id = identification_tipo_id
                self.identificacion_tercero = brw_parent.vat and brw_parent.vat[:-3]
            else:
                self.identificacion_tercero = brw_parent.vat
            self.nombre_tercero = self.partner_id.name

    def unlink(self):
        return super(ResPartnerBank, self).unlink()

    def validate_acc_numbers(self):
       for brw_each in self:
           if brw_each.partner_id.country_id==self.env.ref('base.ec'):
               acc_number=brw_each.acc_number
               if not re.fullmatch(r'[0-9]+', acc_number) or re.fullmatch(r'0+', acc_number):
                    raise ValidationError(
                        _("La cuenta bancaria asociada para %s debe contener solo números y no ser todo ceros.") % (
                                brw_each.partner_id.name,))

    @api.model
    def create(self, vals):
        record = super(ResPartnerBank,self).create(vals)
        record.validate_acc_numbers()
        return record

    def write(self, vals):
        res = super(ResPartnerBank,self).write(vals)
        self.validate_acc_numbers()
        return res

    @api.constrains('partner_email')
    def _check_partner_email(self):
        email_regex = r"[^@ \t\r\n]+@[^@ \t\r\n]+\.[^@ \t\r\n]+"
        for record in self:
            if record.partner_email:
                emails = [e.strip() for e in record.partner_email.split(',')]
                for email in emails:
                    if not re.fullmatch(email_regex, email):
                        raise ValidationError(_(f"El correo '{email}' no tiene un formato válido."))

