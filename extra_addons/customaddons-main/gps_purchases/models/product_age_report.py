# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import date_utils
import io
import xlsxwriter
from odoo.http import content_disposition, request
import base64
import datetime


class ProductAgeReport(models.TransientModel):
    _name = 'product.age.report'
    _description = 'Reporte de antigüedad productos'

    company_ids = fields.Many2many(
        'res.company',
        string="Compañías",
        default=lambda self: self.env.company,
        domain=lambda self: [('id', 'in', self.env.user.company_ids.ids)]
    )

    start_date = fields.Date(
        string="Fecha Inicio",
        required=True,
        default=fields.Date.today
    )

    end_date = fields.Date(
        string="Fecha Fin",
        required=True,
        default=fields.Date.today
    )

    quant_ids = fields.One2many(
        'stock.quant', 'id',
        string="Stock Moves",
    )