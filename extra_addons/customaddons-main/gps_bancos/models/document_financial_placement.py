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

class DocumentFinancialPlacement(models.Model):
    _name = "document.financial.placement"

    _description = 'Colocación Financiera'

    quota = fields.Integer(related="document_line_id.quota", store=False, readonly=True,string='Cupón', required=True)
    start_date = fields.Date(string='Inicio', required=True)
    due_date = fields.Date(string='Vencimiento', required=True)
    interest_rate = fields.Float(string='% Tasa', digits=(16, 4), required=True)
    interest_amount = fields.Monetary(string='Interés', required=True)
    principal_amount = fields.Monetary(string='Capital', required=True)
    total = fields.Monetary(string='Flujo Total', required=False,sum="_compute_total",store=True,readonly=True)
    remaining_balance = fields.Monetary(string='Saldo a Amortizar', required=False,default=0.00)
    placed_amount = fields.Monetary(string='Monto Colocado', required=False,default=0.00)
    type_emission = fields.Selection([('1', 'Primera Emisión'),
                                      ('2', 'Segunda Emisión'),
                               ('3','Tercera Emisión')], string="Tipo de Emisión", tracking=True)
    type_class = fields.Selection([('A', 'A'),
                                   ('B', 'B'),
                                   ('C', 'C')], string="Clase", tracking=True)
    number_liquidation = fields.Char(related="liquidation_id.number_liquidation",string='# Liquidación')
    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company, tracking=True
    )
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)
    document_id = fields.Many2one("document.financial", "Documento Bancario", ondelete="cascade")
    document_line_id= fields.Many2one("document.financial.line", "Cuota", ondelete="cascade")
    liquidation_id=fields.Many2one('document.financial.liquidation','# Liquidación', ondelete="cascade")

    _rec_name="quota"

    @api.depends('interest_amount','principal_amount')
    @api.onchange('interest_amount', 'principal_amount')
    def _compute_total(self):
        DEC=2
        for brw_each in self:
            total=  brw_each.interest_amount+brw_each.principal_amount
            brw_each.total=round(total,DEC)