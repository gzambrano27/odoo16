#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    description = fields.Char(
        required=True, readonly=True, states={"draft": [("readonly", False)]}
    )

    @api.model
    def default_get(self, field_list):
        res = super(AccountPaymentOrder, self).default_get(field_list)
        res.update({"date_scheduled": fields.Date.today(), "date_prefered": "fixed"})
        return res

    @api.constrains("date_scheduled")
    def check_date_scheduled(self):
        pass

    def draft2open(self):
        """
        Called when you click on the 'Confirm' button
        Set the 'date' on payment line depending on the 'date_prefered'
        setting of the payment.order
        Re-generate the account payments.
        """
        self = self.with_context(skip_account_move_synchronization=True)
        today = fields.Date.context_today(self)
        for order in self:
            if not order.journal_id:
                raise UserError(
                    _("Missing Bank Journal on payment order %s.") % order.name
                )
            if (
                order.payment_method_id.bank_account_required
                and not order.journal_id.bank_account_id
            ):
                raise UserError(
                    _("Missing bank account on bank journal '%s'.")
                    % order.journal_id.display_name
                )
            if not order.payment_line_ids:
                raise UserError(
                    _("There are no transactions on payment order %s.") % order.name
                )
            # Unreconcile, cancel and delete existing account payments
            order.payment_ids.action_draft()
            order.payment_ids.action_cancel()
            order.payment_ids.unlink()
            # Prepare account payments from the payment lines
            payline_err_text = []
            group_paylines = {}  # key = hashcode
            for payline in order.payment_line_ids:
                try:
                    payline.draft2open_payment_line_check()
                except UserError as e:
                    payline_err_text.append(e.args[0])
                # Compute requested payment date
                if order.date_prefered == "due":
                    requested_date = payline.ml_maturity_date or payline.date or today
                elif order.date_prefered == "fixed":
                    requested_date = order.date_scheduled or today
                else:
                    requested_date = today
                # inbound: check option no_debit_before_maturity
                if (
                    order.payment_type == "inbound"
                    and order.payment_mode_id.no_debit_before_maturity
                    and payline.ml_maturity_date
                    and requested_date < payline.ml_maturity_date
                ):
                    payline_err_text.append(
                        _(
                            "The payment mode '%(pmode)s' has the option "
                            "'Disallow Debit Before Maturity Date'. The "
                            "payment line %(pline)s has a maturity date %(mdate)s "
                            "which is after the computed payment date %(pdate)s.",
                            pmode=order.payment_mode_id.name,
                            pline=payline.name,
                            mdate=payline.ml_maturity_date,
                            pdate=requested_date,
                        )
                    )
                # Write requested_date on 'date' field of payment line
                # norecompute is for avoiding a chained recomputation
                # payment_line_ids.date
                # > payment_line_ids.amount_company_currency
                # > total_company_currency
                with self.env.norecompute():
                    payline.date = requested_date
                # Group options
                hashcode = (
                    payline.payment_line_hashcode()
                    if order.payment_mode_id.group_lines
                    else payline.id
                )
                if hashcode in group_paylines:
                    group_paylines[hashcode]["paylines"] += payline
                    group_paylines[hashcode]["total"] += payline.amount_currency
                else:
                    group_paylines[hashcode] = {
                        "paylines": payline,
                        "total": payline.amount_currency,
                    }
            # Raise errors that happened on the validation process
            if payline_err_text:
                raise UserError(
                    _("There's at least one validation error:\n")
                    + "\n".join(payline_err_text)
                )

            order.env.flush_all()

            # Create account payments
            payment_vals = []
            for paydict in list(group_paylines.values()):
                # Block if a bank payment line is <= 0
                if paydict["total"] <= 0:
                    raise UserError(
                        _(
                            "The amount for Partner '%(partner)s' is negative "
                            "or null (%(amount).2f) !",
                            partner=paydict["paylines"][0].partner_id.name,
                            amount=paydict["total"],
                        )
                    )
                payment_vals.append(paydict["paylines"]._prepare_account_payment_vals())
            self.env["account.payment"].create(payment_vals)
        self.write({"state": "open"})
        return True

    def generated2uploaded(self):
        return super(
            AccountPaymentOrder,
            self.with_context(skip_account_move_synchronization=True),
        ).generated2uploaded()
