# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID


class DocumentBank(models.Model):

    _name = "document.bank"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Operacion Financiera"

    internal_type=fields.Selection([
        ('out','Pagos'),
        ('in', 'Cobros'),

    ],string="Tipo de Operacion Interna",default="out")

    type=fields.Selection([('pagares','Pagarés'),
                           ('emision', 'Emisión de Obligaciones'),
                           ('prestamo', 'Préstamos Bancarios')
                           ],string="Tipo",default="emision")

    state = fields.Selection([('draft','Preliminar'),
                              ('posted','Publicado'),
                              ('cancelled','Anulado')], string="Estado", default="draft",tracking=True)

    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)

    date_negotiation = fields.Date("Fecha de Negociación", required=True, default=fields.Date.today())
    date_process=fields.Date("Fecha de Emisión",required=True,default=fields.Date.today())
    date_maturity = fields.Date("Fecha de Vencimiento", required=False, compute="_compute_date_maturity",store=True)

    name=fields.Char("# Documento",required=True)
    number_invoice = fields.Char("# Factura", required=False)

    partner_id = fields.Many2one(
        "res.partner",
        string="Emisor",
        required=True,
        copy=False
    )

    line_ids = fields.One2many("document.bank.line", "document_id", "Detalle")

    total = fields.Monetary(string="Total",store=True, compute="_compute_total")
    total_to_paid = fields.Monetary(string="Total a Pagar",store=True, compute="_compute_total")
    total_paid = fields.Monetary(string="Total Pagado",store=True, compute="_compute_total")
    total_pending = fields.Monetary(string="Total Pendiente",store=True, compute="_compute_total")

    comments=fields.Text("Comentarios")

    amount = fields.Monetary("Valor Nominal", default=0.00)
    percentage_amortize = fields.Float("% por Amortizar", default=0.00, digits=(4, 2) )
    percentage_interest = fields.Float("% de Interes", default=00, digits=(4, 2))
    percentage_interest_quota = fields.Float("% de Interes Cuota", default=0.00, digits=(4, 6))
    capital = fields.Monetary("Pago de  Capital", default=0.00)
    periods = fields.Integer("# Periodos", default=0)
    years = fields.Integer("Años", default=0)

    type_document = fields.Selection([('compute', 'Calculado'),
                                      ('file', 'Archivo')], string="Tipo", default="compute")

    invoice_ids = fields.Many2many("account.move", "document_bank_invoice_rel", "document_id", "invoice_id",
                                   "Facturas")

    _check_company_auto = True

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        raise ValidationError(_("No puedes duplicar este documento"))

    def action_posted(self):
        for brw_each in self:
            if not brw_each.line_ids:
                raise ValidationError(_("Debes generar al menos una linea"))
            brw_each.write({"state": "posted"})
        return True

    def action_draft(self):
        for brw_each in self:
            if brw_each.total_paid!=0.00:
                raise ValidationError(_("No puedes reversar un documento financiero con al menos un valor pagado"))
            brw_each.write({"state":"draft"})
        return True

    def action_cancel(self):
        for brw_each in self:
            if brw_each.total_paid != 0.00:
                raise ValidationError(_("No puedes anular un documento financiero con al menos un valor pagado"))
            brw_each.write({"state":"cancelled"})
        return True

    def unlink(self):
        for brw_each in self:
            if self._context.get("validate_unlink", True):
                if brw_each.state != 'draft':
                    raise ValidationError(_("No puedes borrar un registro que no sea preliminar"))
        return super(DocumentBank, self).unlink()

    @api.onchange('line_ids', 'date_process', 'line_ids.date_process')
    @api.depends('line_ids', 'date_process', 'line_ids.date_process')
    def _compute_date_maturity(self):
        for brw_each in self:
            date_maturity = brw_each.date_process
            # Ordenamos las líneas de documentos relacionados por `date_process` en orden descendente
            line_ids_sorted = sorted(brw_each.line_ids, key=lambda line: line.date_process, reverse=True)
            if line_ids_sorted:
                date_maturity = line_ids_sorted[0].date_process
            brw_each.date_maturity = date_maturity

    @api.onchange('line_ids', 'line_ids.total', 'line_ids.total_to_paid', 'line_ids.total_paid',
                  'line_ids.total_pending')
    def onchange_line_ids(self):
        self.update_total()

    @api.depends('line_ids', 'line_ids.total', 'line_ids.total_to_paid', 'line_ids.total_paid',
                 'line_ids.total_pending','line_ids.payment_ids')
    def _compute_total(self):
        for brw_each in self:
            brw_each.update_total()

    def update_total(self):
        DEC = 2
        for brw_each in self:
            total, total_to_paid, total_paid, total_pending = 0.00, 0.00, 0.00, 0.00
            for brw_line in brw_each.line_ids:
                total += brw_line.total
                total_to_paid += brw_line.total_to_paid
                total_paid += brw_line.total_paid
                total_pending += brw_line.total_pending
            brw_each.total = round(total, DEC)
            brw_each.total_to_paid = round(total_to_paid, DEC)
            brw_each.total_paid = round(total_paid, DEC)
            brw_each.total_pending = round(total_pending, DEC)

    @api.onchange('number_invoice')
    def onchange_number_invoice(self):
        if not self.number_invoice:
            return
        partes = self.number_invoice.split('-')

        # Completar con ceros a la izquierda según el número de dígitos esperado
        partes_completadas = [
            parte.zfill(3) if i < 2 else parte.zfill(9) for i, parte in enumerate(partes)
        ]

        # Unir las partes con guion
        self. number_invoice='-'.join(partes_completadas)
