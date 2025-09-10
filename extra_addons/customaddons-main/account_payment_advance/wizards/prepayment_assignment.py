#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class AccountPrepaymentAssignment(models.TransientModel):
    """Prepayment assignment"""

    _name = "account.prepayment.assignment"
    _description = __doc__

    move_id = fields.Many2one(comodel_name="account.move")
    prepayment_aml_id = fields.Many2one(
        comodel_name="account.move.line", string="Prepayment"
    )
    amount = fields.Float(string="Amount")
    date = fields.Date(string="Date", default=fields.Date.today())

    def _max_amount(self):
        return min(
            abs(self.prepayment_aml_id.amount_residual),
            abs(self.move_id.amount_residual),
        )

    @api.onchange("move_id")
    def _onchange_move_id(self):
        if self.move_id:
            lines, invoice_type = self.move_id._get_prepayment_lines()
            return {"domain": {"prepayment_aml_id": [("id", "in", lines.ids)]}}

    @api.onchange("prepayment_aml_id")
    def _onchange_credit_aml_id(self):
        if self.prepayment_aml_id:
            self.amount = self._max_amount()

    @api.constrains("move_id", "amount", "prepayment_aml_id")
    def _check_amount(self):
        if self.amount > self._max_amount():
            raise UserError(
                "The maximum reconciliation amount for this payment "
                "is {} on invoice {}".format(
                    self._max_amount(), self.move_id.display_name
                )
            )

    def button_confirm(self):
        self.move_id.prepayment_assign_move(
            prepayment_aml_id=self.prepayment_aml_id,
            amount=self.amount,
            date=self.date,
        )
        return True
