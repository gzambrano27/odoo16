#!/usr/bin/env python
# -*- coding: utf-8 -*-
import base64
import logging
from io import BytesIO
from zipfile import BadZipFile

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from openpyxl_dictreader import DictReader


_logger = logging.getLogger(__name__)


class AccountPaymentImportInvoices(models.Model):
    """Payment Import Invoices"""

    _name = "account.payment.import.invoices"
    _description = __doc__

    payment_id = fields.Many2one(comodel_name="account.payment", string="Payment")
    xlsx_file = fields.Binary(string=_("File"), required=True)
    xlsx_filename = fields.Char(string=_("Filename"))
    message = fields.Text(string=_("Error"))
    state = fields.Selection(
        selection=[("draft", "draft"), ("error", "error")], string=_("State")
    )

    def button_confirm(self):
        if not self.xlsx_file:
            raise UserError(_("Please, select file to Import"))
        data = base64.b64decode(self.xlsx_file)
        file_input = BytesIO(data)
        file_input.seek(0)
        try:
            reader = DictReader(file_input, data_only=True)
        except BadZipFile:
            raise Warning(_("The file to import must have an xlsx extension!"))
        inv_obj = self.env["account.move"]
        error = ""
        move_type = {"outbound": "in_invoice", "inbound": "out_invoice"}
        lines = []
        pay = self.payment_id
        pay_amount = 0
        for row in reader:
            invoice = row.get("invoice")
            amount = row.get("amount")
            inv = inv_obj.search(
                [
                    ("name", "=ilike", "%" + invoice),
                    ("partner_id", "=", pay.partner_id.id),
                    ("move_type", "=", move_type[pay.payment_type]),
                    ("state", "=", "posted"),
                    ("payment_state", "not in", ["paid", "reversed", "in_payment"]),
                ],
                limit=1,
            )
            if not inv:
                error += _(
                    "An invoice was not found with the number {}, or is not with a pending balance!.\n".format(
                        row.get("invoice")
                    )
                )
            invoice_accounts = (
                inv.mapped("line_ids")
                .filtered(
                    lambda x: x.account_id.internal_type in ("payable", "receivable")
                )
                .mapped("account_id")
            )
            if invoice_accounts and pay.destination_account_id not in invoice_accounts:
                error += _(
                    "The account {} in invioce {} is different from the payment account of the {} payment!\n".format(
                        ",".join(
                            map(
                                str,
                                invoice_accounts.mapped("display_name"),
                            )
                        ),
                        inv.display_name,
                        pay.destination_account_id.display_name,
                    )
                )
            if not amount > 0:
                error += _(
                    "The amount to be paid for the invoice {} must be greater than 0!.\n".format(
                        invoice
                    )
                )
            if inv and abs(inv.amount_residual) < amount:
                error += _(
                    "The amount to be paid {} is higher than residual amount {} of the invoice {}!.\n".format(
                        amount, abs(inv.amount_residual), invoice
                    )
                )
            if inv and row.get("amount") > 0:
                lines.append(
                    (
                        0,
                        0,
                        {
                            "invoice_id": inv.id,
                            "already_paid": sum(
                                [
                                    payment["amount"]
                                    for payment in inv._get_reconciled_info_JSON_values()
                                ]
                            ),
                            "amount_residual": inv.amount_residual,
                            "amount_untaxed": inv.amount_untaxed,
                            "amount_tax": inv.amount_tax,
                            "currency_id": inv.currency_id.id,
                            "amount_total": inv.amount_total,
                            "amount_paid": amount,
                        },
                    )
                )
                pay_amount += amount
        if error:
            self.state = "error"
            self.message = error
            module = __name__.split("addons.")[1].split(".")[0]
            action_name = "{}.action_account_payment_import_invoices".format(module)
            action = self.sudo().env.ref(action_name, False).read()[0]
            action["res_id"] = self.id
            return action
        pay.write({"reconcile_invoice_ids": lines, "amount": pay_amount})
        return {"type": "ir.actions.act_window_close"}
