# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_

class AccountMove(models.Model):
    _inherit="account.move"

    @api.model
    def _get_prepayment_aml_account_payable_id(self):
        inv = self
        return inv.partner_id.property_account_payable_id.id

    @api.model
    def _get_prepayment_aml_account_receivable_id(self):
        inv = self
        return inv.partner_id.property_account_receivable_id.id

    def prepayment_assign_move_new(self, prepayment_aml_id=False, amount=False, date=False,new_journal_id=False):
        """
        This function must be called only when the account of the aml
        is prepayment, in order to generate the assignation move and
        reconcile the transactions.

        Here we don't do any validation, the function must be called
        only when this process should be executed.

        """
        aml_obj = self.env["account.move.line"]
        inv = self
        credit_aml_acc = prepayment_aml_id.account_id.id
        it = inv.move_type
        if it == "in_invoice":
            account = inv._get_prepayment_aml_account_payable_id()
        elif it == "out_invoice":
            account = inv._get_prepayment_aml_account_receivable_id()
        else:
            return

        inv_acc = account
        payment = prepayment_aml_id.payment_id
        partner = payment.partner_id if payment else inv.partner_id #cambio para que se cruce de la cuenta de anticipo 
        journal = payment and payment.journal_id or prepayment_aml_id.journal_id
        if prepayment_aml_id.journal_id and new_journal_id:
            journal=new_journal_id
        date = date or fields.Date.context_today(self)

        ref = _(
            "Prepayment Assign of: {}, Inv.: {}".format(
                payment and payment.name or prepayment_aml_id.move_id.name,
                inv.display_name,
            )
        )
        move = (
            self.env["account.move"]
            .with_context(skip_account_move_synchronization=True)
            .create(
                {
                    "date": date,
                    "ref": ref,
                    "company_id": inv.company_id.id,
                    "journal_id": journal.id,
                    "partner_id": partner.id,
                    "prepayment_assignment": True,
                }
            )
        )
        payable_receivable_line = aml_obj.with_context(
            **{
                "check_move_validity": False,
                "skip_account_move_synchronization": True,
            }
        ).create(
            {
                "name": ref,
                "partner_id": partner.id,
                "move_id": move.id,
                "credit": amount if it == "out_invoice" else 0,
                "debit": 0 if it == "out_invoice" else amount,
                "account_id": inv_acc,
                "payment_id": payment.id,
                "date": date,
            }
        )
        advance_line = aml_obj.with_context(
            **{
                "check_move_validity": False,
                "skip_account_move_synchronization": True,
            }
        ).create(
            {
                "name": ref,
                "partner_id": partner.id,
                "move_id": move.id,
                "credit": 0 if it == "out_invoice" else amount,
                "debit": amount if it == "out_invoice" else 0,
                "account_id": credit_aml_acc,
                "payment_id": payment.id,
                "date": date,
            }
        )
        move.with_context(skip_account_move_synchronization=True).action_post()
        acc2rec = advance_line
        acc2rec |= prepayment_aml_id
        acc2rec.reconcile()
        inv.js_assign_outstanding_line(
            payable_receivable_line.id,
        )
        return True