# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import re
from ..models import DEFAULT_MODE_PAYMENTS

class AccountPaymentRequestWorkflowWizard(models.Model):
    _name = 'account.payment.request.workflow.wizard'
    _description = "Asistente de Workflow para Solicitud de Pagos"

    @api.model
    def _get_default_payment_amount(self):
        brw_payment = self.env["account.payment.bank.macro.summary"].sudo().browse(self.env.context.get('active_id'))
        return brw_payment.amount

    @api.model
    def _get_default_mode_payment(self):
        active_ids = self._context.get("active_ids", [])
        for brw_summary in self.env["account.payment.bank.macro.summary"].browse(active_ids):
            default_mode_payment = brw_summary.bank_macro_id.default_mode_payment
            return default_mode_payment
        return None

    motive_id=fields.Many2one('account.payment.request.type','Motivo de Reverso',domain=[('type','=','anulacion')])
    comments=fields.Text("Comentarios")
    ref = fields.Char("Referencia")
    date=fields.Date('Fecha')
    full_reversed = fields.Boolean("Reverso Completo", default=True)
    amount = fields.Float('Monto Reverso', default=_get_default_payment_amount, required=True)
    default_mode_payment = fields.Selection(DEFAULT_MODE_PAYMENTS, string="Forma de Pago",
                                            default=_get_default_mode_payment)

    def process(self):
        DEC=2
        self.ensure_one()
        active_ids=self._context.get("active_ids",[])
        if not active_ids:
            raise ValidationError("Debes seleccionar al menos un registro")
        OBJ_PAYMENT_CANCEL=self.env["account.payment.cancel.wizard"]
        payments=self.env["account.payment"]
        for brw_summary in self.env["account.payment.bank.macro.summary"].sudo().browse(active_ids):
            payment_ids=brw_summary.line_ids.mapped('payment_id')
            brw_summary.line_ids.write({"reversed":True})
            brw_summary.write({
                "reversed_motive_id":self.motive_id.id,
                "reversed_comments":self.comments,
                "reversed_date":self.date,
                "reversed_ref":self.ref,
                "reversed":True
            })
            for brw_payment in payment_ids:
                vals={
                    "date":self.date,
                    "comments":self.comments,
                    "payment_id":brw_payment.id,
                    "full_reversed":(round(brw_payment.amount,DEC)==round(brw_summary.amount,DEC)),
                    "amount": self.amount
                }
                brw_cancel_wizard=OBJ_PAYMENT_CANCEL.create(vals)
                brw_cancel_wizard.action_reverse_payment()
                brw_payment.reversed_payment_id.write({"bank_reference": self.ref})
                payments+=brw_payment.reversed_payment_id
                payments+= brw_payment.mapped('reversed_payment_ids')
        payments_ids = payments.ids + [-1, -1]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_account_payments_payable"
        )
        action["domain"] = [('id', 'in', payments_ids)]
        return action
