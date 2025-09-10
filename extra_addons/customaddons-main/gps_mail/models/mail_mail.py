# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_, SUPERUSER_ID
import base64

class MailMail(models.Model):
    _inherit="mail.mail"

    @api.model
    def _get_default_mail_server_id(self):
        print(self._context)
        return False

    mail_server_id=fields.Many2one("ir.mail_server",default=_get_default_mail_server_id)