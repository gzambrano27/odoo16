# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError,UserError
from datetime import datetime

import re
import unicodedata
import base64
import io
import csv
from datetime import datetime

import pytz


class DocumentBankReconciliationLine(models.Model):
    _name = 'document.bank.reconciliation.line'
    _description = "Detalle de Conciliación Bancaria"

    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    @api.model
    def _get_default_date(self):
        return fields.Date.context_today(self)

    name=fields.Char("Nombre",required=False,size=255)
    company_id = fields.Many2one("res.company","Compañia",required=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)
    document_id = fields.Many2one("document.bank.reconciliation", "Conciliación Bancaria", ondelete="cascade")

    sequence = fields.Integer(string="No.")
    date = fields.Date(string="Fecha", required=True)
    reference = fields.Char(string="Referencia")
    location = fields.Char(string="Lugar")
    detail = fields.Char(string="Detalle")
    transaction_type = fields.Selection([
        ('debit', '+'),
        ('credit', '-')
    ], string="Tipo Movimiento", required=True)
    amount = fields.Monetary(string="Valor", required=True)
    available_balance = fields.Monetary(string="Saldo Disponible")
    book_balance = fields.Monetary(string="Saldo Contable")
    description = fields.Char(string="Descripción")


    signed_amount = fields.Monetary(
        string="Valor con Signo",
        compute="_compute_signed_amount",
        store=True
    )

    account_id = fields.Many2one(related="document_id.account_id", store=False, readonly=True)
    journal_id = fields.Many2one(related="document_id.journal_id", store=False, readonly=True)
    group_id = fields.Many2one(
        'document.bank.reconciliation.line.group',
        string="Grupo de Conciliación",
        ondelete="set null"
    )
    full_reconciled=fields.Boolean(related="group_id.full_reconciled",store=False,readonly=True,default=False)

    type_id=fields.Many2one('document.bank.reconciliation.type','Tipo de Documento')

    accountable_amount = fields.Monetary(string="Valor por Contabilizar",store=True,readonly=True,default=0.00,compute="_compute_accounted_amount")
    accounted_amount  = fields.Monetary(string="Valor Contabilizado",store=True,readonly=True,default=0.00,compute="_compute_accounted_amount")

    payment_line_ids=fields.One2many('account.payment.lines','reconciliation_line_id','Detalle de Pagos')

    @api.depends('payment_line_ids','payment_line_ids.payment_id',
                 'payment_line_ids.payment_id.state','payment_line_ids.payment_id.reversed_payment_id',
                 'payment_line_ids.amount')
    def _compute_accounted_amount(self):
        DEC=2
        for brw_each in self:
            accounted_amount=0.00
            if brw_each.payment_line_ids:
                for brw_line in brw_each.payment_line_ids:
                    if brw_line.payment_id.state == 'posted':
                        accounted_amount+= brw_line.amount  #ya viene con signo contrario
            #print(brw_each.signed_amount,accounted_amount)
            accounted_amount=abs(accounted_amount)
            accountable_amount=brw_each.amount-accounted_amount
            brw_each.accountable_amount=round(accountable_amount,DEC)
            brw_each.accounted_amount = round(accounted_amount,DEC)

    # @api.constrains('accountable_amount')
    # def validate_accountable_amount(self):
    #     for brw_each in self:
    #         if brw_each.accountable_amount<0.00:
    #             raise ValidationError(_("El Valor por Contabilizar debe ser mayor o igual a 0.00"))

    @api.depends('transaction_type', 'amount')
    def _compute_signed_amount(self):
        DEC = 2
        for rec in self:
            signed_amount=(rec.transaction_type=='debit' and 1.00 or -1.00)*rec.amount
            rec.signed_amount = round(signed_amount, DEC)

    _order="sequence asc"

    _rec_name = "reference"
    _check_company_auto = True

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        raise ValidationError(_("No puedes duplicar este documento"))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.document_id:
                rec.document_id.action_generate_summary()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'type_id' in vals or 'amount' in vals:
            for rec in self:
                if rec.document_id:
                    rec.document_id.action_generate_summary()
        return res


