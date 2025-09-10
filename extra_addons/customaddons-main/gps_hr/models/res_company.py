# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from odoo.exceptions import ValidationError,UserError
from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit="res.company"

    payslip_journal_id=fields.Many2one("account.journal","Diario de Nómina")
    vacation_passed_days = fields.Integer("Dias para habilitar las vacaciones del periodo", default=1)
    vacation_min_work_days = fields.Integer("Dias minimos trabajados", default=1)
    account_by_payslip_run = fields.Boolean("Contabilizar por Lote", default=True)
