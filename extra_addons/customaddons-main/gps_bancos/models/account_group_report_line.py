# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime


class AccountGroupReportLine(models.Model):
    _name = 'account.group.report.line'
    _description = "Detalle de Reporte de Cuentas"

    report_id=fields.Many2one("account.group.report","Reporte",ondelete="cascade")
    name = fields.Char("Descripcion", required=True)
    template_ids=fields.Many2many("account.account","report_template_account_acc_rel","report_line_id","account_id","Cuentas")

    _rec_name = "name"