# Copyright 2019 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    amount_residual = fields.Monetary(
        compute="_amount_residual",
        string="Residual Amount",
        store=True,
        currency_field="currency_id",
        help="The residual amount on a journal item "
        "expressed in the company currency.",
    )

    @api.depends(
        "move_id",
        "move_id.line_ids",
        "move_id.line_ids.amount_residual",
        "move_id.line_ids.amount_residual_currency",
    )
    def _amount_residual(self):
        for row in self:
            amount_residual = 0.0
            amount_residual_currency = 0.0
            pay_acc = row.journal_id.default_account_id
            for aml in row.move_id.line_ids.filtered(
                lambda x: x.account_id.reconcile and x.account_id != pay_acc
            ):
                amount_residual += aml.amount_residual
                amount_residual_currency += aml.amount_residual_currency
            if row.payment_type == "inbound":
                amount_residual *= -1
                amount_residual_currency *= -1
            if row.currency_id != row.company_id.currency_id:
                row.amount_residual = amount_residual_currency
            else:
                row.amount_residual = amount_residual
        return True
