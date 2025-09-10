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


class DocumentBankReconciliationLineGroup(models.Model):
    _name = 'document.bank.reconciliation.line.group'
    _description = "Grupo de Conciliación Bancaria"

    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    company_id = fields.Many2one("res.company", "Compañia", required=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)
    document_id = fields.Many2one("document.bank.reconciliation", "Conciliación Bancaria", ondelete="cascade")

    date = fields.Date(string="Fecha", required=True)
    reference = fields.Char(string="Referencia")
    transaction_type = fields.Selection([
        ('debit', '+'),
        ('credit', '-')
    ], string="Tipo Movimiento", required=True)
    amount = fields.Monetary(string="Valor", required=True)
    description = fields.Char(string="Descripción")

    line_ids = fields.One2many(
        'document.bank.reconciliation.line',
        'group_id',
        string="Líneas del Grupo"
    )

    move_ids = fields.Many2many(
        'account.move',
        'rel_reconciliation_line_group_move',
        'reconciliation_id',
        'move_id',
        string='Asientos Relacionados'
    )

    move_line_ids = fields.Many2many(
        'account.move.line',
        'rel_reconciliation_line_group_move_line',
        'reconciliation_id',
        'move_line_id',
        string='Líneas de Asiento Relacionadas'
    )


    parent_move_ids = fields.Many2many(
        'account.move',

        string="Asientos de Bancos dentro del rango",compute="_compute_parent_move_ids",store=False,readonly=True
    )

    other_move_line_ids = fields.Many2many(
        'account.move.line',
        'rel_rec_line_group_other_move_line',
        'reconciliation_id',
        'move_line_id',
        string='Otras Líneas de Asiento Relacionadas'
    )

    total_signed_related_amount = fields.Monetary(
        string="Suma de Débitos/Créditos",
        compute="_compute_totals_and_difference",
        store=True
    )

    difference_amount = fields.Monetary(
        string="Diferencia con Valor",
        compute="_compute_totals_and_difference",
        store=True
    )

    signed_amount = fields.Monetary(
        string="Valor con Signo",
        compute="_compute_signed_amount",
        store=True
    )

    parent_date_from=fields.Date(related="document_id.date_from",store=False,readonly=True)
    parent_date_to = fields.Date(related="document_id.date_to", store=False, readonly=True)

    @api.depends('document_id', 'document_id.move_line_ids')
    def _compute_parent_move_ids(self):
        for rec in self:
            parent_move_ids=rec.document_id.move_line_ids.mapped('move_id')
            rec.parent_move_ids=parent_move_ids

    @api.depends('transaction_type', 'amount')
    def _compute_signed_amount(self):
        DEC = 2
        for rec in self:
            signed_amount = (rec.transaction_type == 'debit' and 1.00 or -1.00) * rec.amount
            rec.signed_amount = round(signed_amount, DEC)

    account_id = fields.Many2one(related="document_id.account_id", store=False, readonly=True)
    journal_id = fields.Many2one(related="document_id.journal_id", store=False, readonly=True)

    bank_macro_id = fields.Many2one('account.payment.bank.macro', 'Pago con Macro')
    bank_employee_id = fields.Many2one('hr.employee.payment', 'Pago a Empleados')
    payment_ids = fields.Many2many('account.payment','pay_reconc_group_rel','group_id','payment_id', 'Pagos')

    full_reconciled=fields.Boolean('Reconciliado',default=False)

    @api.onchange('bank_macro_id')
    def onchange_bank_macro_id(self):
        move_ids = self.env["account.move"]
        if self.bank_macro_id:
            move_ids += self.bank_macro_id.line_ids.mapped('payment_id.move_id')
        self.move_ids = move_ids

    @api.onchange('bank_employee_id')
    def onchange_bank_employee_id(self):
        move_ids = self.env["account.move"]
        if self.bank_employee_id:
            move_ids += self.bank_employee_id.move_id
        self.move_ids = move_ids

    @api.onchange('payment_ids')
    def onchange_payment_ids(self):
        move_ids = self.env["account.move"]
        if self.payment_ids:
            move_ids += self.payment_ids.mapped('move_id')
        self.move_ids = move_ids

    @api.onchange('move_ids')
    def onchange_move_ids(self):
        move_line_ids = self.env["account.move.line"]
        if self.move_ids:
            move_line_ids += self.move_ids.line_ids.filtered(lambda x: x.account_id == self.account_id)
        self.move_line_ids = move_line_ids

    @api.depends('other_move_line_ids','move_line_ids','other_move_line_ids.debit', 'other_move_line_ids.credit', 'move_line_ids.debit', 'move_line_ids.credit', 'transaction_type', 'amount')
    @api.onchange('other_move_line_ids','move_line_ids','other_move_line_ids.debit', 'other_move_line_ids.credit', 'move_line_ids.debit', 'move_line_ids.credit', 'transaction_type', 'amount')
    def _compute_totals_and_difference(self):
        DEC = 2
        for rec in self:
            total = 0.0
            for line in rec.move_line_ids:
                total += (line.debit - line.credit)
            for line in rec.other_move_line_ids:
                total += -(line.debit - line.credit)
            rec.total_signed_related_amount = round(total, DEC)
            rec.difference_amount = round(rec.signed_amount - total, DEC)
            rec.full_reconciled = (rec.difference_amount == 0.00)

    @api.depends('line_ids.currency_id')
    def _compute_currency_id(self):
        for rec in self:
            # Se toma la moneda de la primera línea si todas comparten la misma moneda
            if rec.line_ids:
                rec.currency_id = rec.line_ids[0].currency_id
            else:
                rec.currency_id = self.env.company.currency_id

