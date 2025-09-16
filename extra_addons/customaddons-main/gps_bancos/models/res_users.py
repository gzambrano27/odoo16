# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID



class ResUsers(models.Model):
    _inherit = "res.users"

    def write(self, vals):
        self = self.with_context(bypass_partner_restriction=True)
        return super(ResUsers,self).write(vals)

    def action_reset_password(self):
        self = self.with_context(bypass_partner_restriction=True)
        return super(ResUsers, self).action_reset_password()

