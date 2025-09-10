# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID


class DocumentBankLinePayment(models.Model):
    _name = "document.bank.line.payment"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Pago de Operacion Financiera"

    line_id = fields.Many2one(
        "document.bank.line",
        string="Detalle de Operacio Financiera", on_delete="cascade"
    )

    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related="company_id.currency_id",store=False,readonly=True)
    date_process = fields.Date("Fecha de Pago", required=True)
    amount = fields.Monetary("Aplicado",  default=0.00,required=True)


    _order="line_id asc,date_process asc"
