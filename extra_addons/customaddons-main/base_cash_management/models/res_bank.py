#!/usr/bin/env python
import logging

from odoo import _, api, fields, models


_logger = logging.getLogger(__name__)


class ResBankCode(models.Model):
    """Bank Code"""

    _name = "res.bank.code"
    _description = __doc__

    bank_main_id = fields.Many2one("res.bank", string="Main Bank", required=True)
    bank_id = fields.Many2one("res.bank", string="Bank", required=True)
    code = fields.Char(string="Code", required=True)

    @api.model
    def get_bank_code(self, main_bank, bank):
        code_id = self.search(
            [("bank_main_id", "=", main_bank.id), ("bank_id", "=", bank.id)], limit=1
        )
        return code_id and code_id.code or None


class ResBank(models.Model):
    _inherit = "res.bank"

    bank_code_ids = fields.One2many(
        "res.bank.code", "bank_main_id", string="Bank Codes"
    )


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    def name_get(self):
        result = []
        for row in self:
            name = ""
            if row.bank_id:
                name += "{} - ".format(row.bank_id.name)
            name += row.acc_number
            result.append((row.id, name))
        return result
