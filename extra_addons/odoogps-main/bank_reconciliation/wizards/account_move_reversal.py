#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    def reverse_moves(self):
        self.ensure_one()
        rec_lines = self.move_ids.mapped("line_ids").filtered(
            lambda x: x.reconciled and x.statement_id
        )
        if rec_lines:
            raise ValidationError(
                _(
                    "You can not modify any record that is part of a bank statement, ref: \n{}".format(
                        "\n".join(map(str, rec_lines.mapped("statement_id.name")))
                    )
                )
            )
        return super(AccountMoveReversal, self).reverse_moves()
