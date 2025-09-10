# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID

class ResBankCode(models.Model):
    _inherit = "res.bank.code"

    code=fields.Char(string="Codigo")
    bank_id = fields.Many2one("res.bank",string="Banco")
    bank_main_id = fields.Many2one("res.bank", string="Banco Principal")

    _rec_name="code"