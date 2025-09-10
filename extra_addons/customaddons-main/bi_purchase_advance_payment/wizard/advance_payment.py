# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo import api, fields, models, _


class AdvancePayment(models.TransientModel):
    _name = 'advance.payment'
    _description = 'Advance Payment'

    journal_id = fields.Many2one('account.journal', string="Payment Journal", required=True,
                                 domain=[('type', 'in', ['cash', 'bank'])])
    pay_amount = fields.Float(string="Payable Amount", required=True)
    date_planned = fields.Datetime(string="Advance Payment Date", index=True, default=fields.Datetime.now,
                                   required=True)
    referencia = fields.Char(string="Memo")
    bank_reference = fields.Char(
        string="Referencia Bancaria",
        copy=False,
    )
    prepayment_account_id = fields.Many2one(
        "account.account",
        string="Cuenta de Anticipo",
        domain="[('deprecated','=',False), ('prepayment_account','=',True)]",
        help="Counterpart for the prepayment move, for example: Prepayment for customers or vendors.",
    )
    is_prepayment = fields.Boolean("Es Anticipo?")

    @api.constrains('pay_amount')
    def check_amount(self):
        purchase_obj = self.env['purchase.order']
        purchase_ids = self.env.context.get('active_ids')
        if purchase_ids:
            purchase_id = purchase_ids[0]
            purchase = purchase_obj.browse(purchase_id)
            tot_purchase = purchase.amount_total
            payments = self.env['account.payment'].search([('purchase_id','=',purchase_id)])
            val_pay = 0
            val_res = 0
            for x in payments:
                if x.move_id.state=='posted':
                    val_pay = val_pay + x.amount
                    val_res = val_res + abs(x.amount_residual)
        if self.pay_amount <= 0:
            raise ValidationError(_("Please Enter Postive Amount"))
        if val_pay > tot_purchase:
            raise ValidationError(_("No puedes pagar mas del valor de la OC!!"))
        # if (tot_purchase - val_res) > self.pay_amount and val_res > 0:
        #     raise ValidationError(_("El valor a pagar es mayor al saldo de la OC!!"))

    def make_payment(self):
        payment_obj = self.env['account.payment']
        purchase_ids = self.env.context.get('active_ids')
        if purchase_ids:
            payment_res = self.get_payment(purchase_ids)
            payment = payment_obj.create(payment_res)
            payment.action_post()
        return {
            'type': 'ir.actions.act_window_close',
        }

    def get_payment(self, purchase_ids):
        purchase_obj = self.env['purchase.order']
        purchase_id = purchase_ids[0]
        purchase = purchase_obj.browse(purchase_id)
        payment_res = {
            'payment_type': 'outbound',
            'partner_id': purchase.partner_id.id,
            'partner_type': 'supplier',
            'journal_id': self.journal_id.id,
            'company_id': purchase.company_id.id,
            'currency_id': purchase.currency_id.id,
            'date': self.date_planned,
            'amount': self.pay_amount,
            'purchase_id': purchase.id,
            'payment_method_id': self.env.ref('account.account_payment_method_manual_out').id,
            'ref': self.referencia,
            #aumentado wgu
            'is_prepayment':self.is_prepayment,
            'prepayment_account_id' : self.prepayment_account_id.id,
            'bank_reference':self.bank_reference
        }
        return payment_res
