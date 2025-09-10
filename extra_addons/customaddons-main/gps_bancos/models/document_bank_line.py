# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID


class DocumentBank(models.Model):
    _name = "document.bank.line"
    _description = "Detalle de Operacion Financiera"

    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related="company_id.currency_id",store=False,readonly=True)


    document_id = fields.Many2one("document.bank", "Documento Bancario", ondelete="cascade")

    quota = fields.Integer(string="Cuota", default=1, required=True)
    date_process = fields.Date("Fecha de Vencimiento", default=fields.Date.today(), required=True)

    percentage_amortize=fields.Float("% por Amortizar",default=0.00,digits=(16,6))
    percentage_interest=fields.Float("% de Interes",default=0.00,digits=(16,6))

    payment_capital = fields.Monetary("Pago de Capital",  default=0.00, required=False)
    payment_interest = fields.Monetary("Pago de Intereses", default=0.00, required=False)

    amount= fields.Monetary("Valor", default=0.00)
    total = fields.Monetary("Total", default=0.00,store=True,compute="_compute_total")
    total_to_paid = fields.Monetary("Por Aplicar",  default=0.00, required=False, store=True,compute="_compute_total")
    total_paid = fields.Monetary("Aplicado",  default=0.00, required=False, store=True,compute="_compute_total")
    total_pending = fields.Monetary("Pendiente",  default=0.00, required=False, store=True,compute="_compute_total")

    payment_ids=fields.One2many("document.bank.line.payment","line_id","Pagos")

    total_invoiced = fields.Monetary("Facturado", default=0.00, required=False, store=True, compute="_compute_total_invoice")
    total_to_invoice = fields.Monetary("Por Facturar", default=0.00, required=False, store=True, compute="_compute_total_invoice")

    invoice_ids = fields.One2many("document.bank.line.invoiced", "line_id", "Facturado")

    @api.depends('document_id.state', 'payment_capital', 'payment_interest','payment_ids','payment_ids.amount','amount')
    @api.onchange('document_id.state', 'payment_capital', 'payment_interest', 'payment_ids', 'payment_ids.amount', 'amount')
    def _compute_total(self):
        for brw_each in self:
            brw_each.update_total()

    def update_total(self):
        DEC = 2
        for brw_each in self:
            total = brw_each.amount
            if brw_each.document_id.internal_type=='out':
                total=round(brw_each.payment_capital+brw_each.payment_interest,DEC)
            brw_each.total = total
            total_to_paid = 0.00
            total_paid = 0.00
            if brw_each.document_id.state not in ("draft", "cancelled"):  # paid,#approved
                total_to_paid = brw_each.total  # siempre tomara el valor a pagar como reflejo de lo que debera pagar
                for brw_line in brw_each.payment_ids:
                    total_paid += brw_line.amount
            brw_each.total_to_paid = round(total_to_paid, DEC)
            brw_each.total_paid = round(total_paid, DEC)
            brw_each.total_pending = round(total_to_paid - total_paid, DEC)

    @api.depends('document_id.state', 'total', 'invoice_ids.state','invoice_ids.invoice_date', 'invoice_ids', 'invoice_ids.amount' )
    @api.onchange('document_id.state', 'total', 'invoice_ids.state','invoice_ids.invoice_date', 'invoice_ids', 'invoice_ids.amount' )
    def _compute_total_invoice(self):
        for brw_each in self:
            brw_each.update_invoiced_total()

    def update_invoiced_total(self):
        DEC = 2
        for brw_each in self:
            total_invoiced = 0.00
            total_to_invoice = 0.00
            if brw_each.document_id.internal_type!='out':
                total=brw_each.total
                if brw_each.document_id.state not in ("draft", "cancelled"):  # paid,#approved
                    for brw_line in brw_each.invoice_ids:
                        if brw_line.invoice_id.state=='posted':
                            total_invoiced += brw_line.amount
                total_to_invoice=total-total_invoiced
            brw_each.total_invoiced = round(total_invoiced, DEC)
            brw_each.total_to_invoice = round(total_to_invoice, DEC)


    _order="quota asc"
