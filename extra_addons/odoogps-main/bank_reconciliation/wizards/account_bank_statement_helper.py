#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from calendar import monthrange
from datetime import datetime, timedelta

from odoo import _, api, fields, models


_logger = logging.getLogger(__name__)


class BankStatementHelper(models.TransientModel):
    """Bank Statement Report helper"""

    _name = "account.bank.statement.helper"
    _description = __doc__

    statement_id = fields.Many2one(comodel_name="account.bank.statement")
    journal_id = fields.Many2one(related="statement_id.journal_id")
    report_type = fields.Selection(
        selection=[("pdf", _("PDF")), ("xlsx", _("XLSX"))],
        string=_("Reporte Type"),
        default="pdf",
    )

    def button_confirm(self):
        if self.report_type == "pdf":
            return self.env.ref(
                "bank_reconciliation.action_bank_statement_report"
            ).report_action(self)
        context = self._context
        datas = {"ids": context.get("active_ids", [])}
        datas["model"] = self._name
        datas["form"] = self.read()[0]
        for field in datas["form"].keys():
            if isinstance(datas["form"][field], tuple):
                datas["form"][field] = datas["form"][field][0]

        return self.env.ref(
            "bank_reconciliation.action_bank_statement_report_xlsx"
        ).report_action(self, data=datas)
