# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_, SUPERUSER_ID
import base64

class MailTemplate(models.Model):
    _inherit="mail.template"

    def generate_email(self, res_ids, fields):
        def update_values(each_value):
            if not each_value.get("mail_server_id", False):
                if each_value.get("model",False):
                    brw_model = self.env[each_value["model"]].browse(each_value["res_id"])
                    brw_company = getattr(brw_model, 'company_id')
                    if brw_company:
                        srch_mail_server = self.env["ir.mail_server"].sudo().search([('active', '=', True),
                                                                                     ('smtp_user', '=', brw_company.email)
                                                                                     ])
                        if srch_mail_server:
                            each_value["mail_server_id"] = srch_mail_server[0].id
        values=super(MailTemplate,self).generate_email(res_ids,fields)
        if type(values)==list:
            for each_value in values:
                update_values(each_value)
        else:
            update_values(values)
        return values

