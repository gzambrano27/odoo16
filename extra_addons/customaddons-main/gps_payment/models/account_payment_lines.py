# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api
from odoo.exceptions import ValidationError

class AccountPaymentLines(models.Model):
    _name = "account.payment.lines"
    _description = 'account.payment.lines'

    company_id = fields.Many2one(related="payment_id.company_id",store=False,readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)

    payment_id = fields.Many2one('account.payment',ondelete="cascade")
    account_id = fields.Many2one('account.account', required=True,domain=[ ('child_ids', '=', False)] )
    partner_id = fields.Many2one('res.partner')
    amount = fields.Monetary(required=False,string="Valor",store=True, compute="compute_amount")

    debit = fields.Monetary(required=True, string="Débito")
    credit = fields.Monetary(required=True, string="Crédito")

    name = fields.Char(string="Descripcion")
    ref_contrapartida = fields.Char(string="Referencia")

    analytic_id=fields.Many2one("account.analytic.account","Cuenta Analitica")

    def update_copy_values(self,copy_values_lines):

        return copy_values_lines

    @api.onchange('debit', 'credit' )
    @api.depends('debit', 'credit')
    def compute_amount(self):
        for brw_each in self:
            brw_each.amount=brw_each.debit>0 and brw_each.debit or -brw_each.credit

    @api.onchange('debit')
    def onchange_debit(self):
        if self.debit < 0:
            raise ValidationError("El debito Asignado no puede ser menor a cero.")
        else:
            self.credit=0.00

    @api.onchange('credit')
    def onchange_credit(self):
        if self.credit < 0:
            raise ValidationError("El credito Asignado no puede ser menor a cero.")
        else:
            self.debit=0.00
