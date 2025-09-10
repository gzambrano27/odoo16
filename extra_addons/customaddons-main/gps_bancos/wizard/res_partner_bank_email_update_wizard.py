from odoo import models, fields, api,SUPERUSER_ID,_
from odoo.exceptions import ValidationError
import re


class PartnerBankEmailUpdateWizard(models.TransientModel):
    _name = 'res.partner.bank.email.update.wizard'
    _description = 'Actualizar Correo de Cuentas Bancarias'

    bank_ids = fields.Many2many('res.partner.bank', string="Cuentas Bancarias", required=True,
                                 domain="[]", default=lambda self: self.env.context.get('active_ids', [])
                                )
    partner_email = fields.Char(string="Nuevo Correo", required=True)

    @api.constrains('partner_email')
    def _check_partner_email(self):
        email_regex = r"[^@ \t\r\n]+@[^@ \t\r\n]+\.[^@ \t\r\n]+"
        for record in self:
            if record.partner_email:
                emails = [e.strip() for e in record.partner_email.split(',')]
                for email in emails:
                    if not re.fullmatch(email_regex, email):
                        raise ValidationError(_(f"El correo '{email}' no tiene un formato válido."))

    def action_update_email(self):
        SUPERUSER_ID=1
        for bank in self.bank_ids:
            bank.with_user(SUPERUSER_ID).write({"partner_email":self.partner_email})
