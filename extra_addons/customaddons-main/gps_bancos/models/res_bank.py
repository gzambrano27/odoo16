# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID



class ResBank(models.Model):
    _inherit = "res.bank"

    use_macro_format=fields.Boolean("Tiene macro de banco",default=False)

    def get_all_codes(self):
        self.ensure_one()
        if not self.use_macro_format:
            raise ValidationError(_("EL banco %s no esta configurado para pagar con bancos") % (self.name,))
        return super(ResBank,self).get_all_codes()


