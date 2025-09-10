# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID


class DocumentFinancialLineInvoiced(models.Model):
    _name = "document.financial.line.invoiced"

    _description = "Factura de Cobro Programado"

    line_id = fields.Many2one(
        "document.financial.line",
        string="Detalle de Operacion Financiera", on_delete="cascade"
    )

    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related="company_id.currency_id",store=False,readonly=True)
    invoice_id=fields.Many2one("account.move","Factura",ondelete="cascade")
    invoice_date = fields.Date(related="invoice_id.invoice_date",string="Fecha de Facturado", required=False,store=False,readonly=True)
    state = fields.Selection(related="invoice_id.state", string="Estado de Facturado", required=False,store=False,
                               readonly=True)

    amount = fields.Monetary("Aplicado",  default=0.00,required=True)
    amount_base = fields.Monetary("Valor Base", default=0.00, required=True)
    amount_iva = fields.Monetary("Valor IVA", default=0.00, required=True)
    amount_retenido = fields.Monetary("Valor Retenido", default=0.00, required=True)

    _order="line_id asc,invoice_id asc"
