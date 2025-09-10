# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID



class ResBank(models.Model):
    _inherit = "res.bank"

    def get_all_codes(self):
        self.ensure_one()
        values={}
        for brw_line in self.bank_code_ids:
            values[brw_line.bank_id.id]=brw_line.code
        return values