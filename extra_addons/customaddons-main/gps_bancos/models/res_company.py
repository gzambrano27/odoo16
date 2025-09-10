# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID



class ResCompany(models.Model):
    _inherit = "res.company"

    def get_mail_bank_alert_not(self):
        self.ensure_one()
        return self.env['ir.config_parameter'].sudo().get_param('correo.envio.notificacion.partner')

    def get_payment_conf(self):
        self.ensure_one()
        OBJ_CONFIG = self.env["account.configuration.payment"].sudo()
        brw_conf = OBJ_CONFIG.search([
            ('company_id', '=',self.id)
        ])
        return brw_conf

