"""
Created on Nov 16, 2020

@author: Zuhair Hammadi
"""
from odoo import fields, models
from odoo.fields import Command


class AccountBankStatementGenerate(models.TransientModel):
    _name = "account.bank.statement.generate"
    _description = "Bank Statement Generate Wizard"

    statement_id = fields.Many2one(
        "account.bank.statement", required=True, ondelete="cascade"
    )
    journal_id = fields.Many2one(related="statement_id.journal_id")
    payment_domain = fields.Char()
    payment_ids = fields.Many2many("account.payment")
    move_domain = fields.Char()
    move_line_ids = fields.Many2many("account.move.line")

    def process(self):
        if self.statement_id and self.statement_id.name == "/":
            seq = self.journal_id.reconciliation_seq
            if not seq:
                seq = (
                    self.env["ir.sequence"]
                    .sudo()
                    .create(
                        {
                            "name": "{}.BST Sequence".format(self.journal_id.code),
                            "implementation": "no_gap",
                            "prefix": "{}.BST/%(range_year)s/".format(
                                self.journal_id.code
                            ),
                            "use_date_range": True,
                            "padding": 4,
                        }
                    )
                )
                self.journal_id.reconciliation_seq = seq.id
            self.statement_id.name = (
                seq.sudo()
                .with_context(ir_sequence_date=self.statement_id.date)
                .next_by_id()
            )
        for payment in self.payment_ids:
            self.env["account.bank.statement.line"].create(
                {
                    "statement_id": self.statement_id.id,
                    "payment_ref": payment.name,
                    "ref": payment.payment_reference,
                    "amount": payment.payment_type == "inbound"
                    and payment.amount
                    or -payment.amount,
                    "matched_payment_ids": [Command.set(payment.ids)],
                    "date": payment.date,
                    "partner_id": payment.partner_id.id,
                }
            )

        for line in self.move_line_ids:
            amount_residual = line.currency_id._convert(
                line.amount_residual_currency,
                self.statement_id.currency_id,
                self.statement_id.company_id,
                self.statement_id.date or fields.Date.today(),
            )
            self.env["account.bank.statement.line"].create(
                {
                    "statement_id": self.statement_id.id,
                    "payment_ref": line.move_id.name,
                    "ref": line.move_id.ref,
                    "amount": self.statement_id.currency_id.round(amount_residual),
                    "matched_move_line_ids": [Command.set(line.ids)],
                    "date": line.date,
                    "partner_id": line.partner_id.id,
                }
            )
        self.statement_id.action_reconcile()
