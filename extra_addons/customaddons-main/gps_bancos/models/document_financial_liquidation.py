# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID


class DocumentFinancialLiquidation(models.Model):
    _name = "document.financial.liquidation"

    _description = 'Liquidacion de Documentos Financieros'

    type_emission = fields.Selection([('1', 'Primera Emisión'),
                                      ('2', 'Segunda Emisión'),
                                         ('3','Tercera Emisión')], string="Tipo de Emisión", tracking=True)
    type_class = fields.Selection([('A', 'A'),
                                   ('B', 'B'),
                                   ('C', 'C'),
                                   ('D', 'D')], string="Clase", tracking=True)
    number_liquidation = fields.Char(string='# Liquidación')
    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company, tracking=True
    )
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)

    date_process = fields.Date(related="document_id.date_process", store=False, readonly=True)

    document_id = fields.Many2one("document.financial", "Documento Bancario", ondelete="cascade")
    parent_state=fields.Selection(related="document_id.state",store=False,readonly=True)

    attachment_ids = fields.Many2many("ir.attachment", "document_financial_liq_attch_rel", "document_line_id",
                                      "attachment_id",
                                      "Adjuntos")

    placement_ids=fields.One2many('document.financial.placement','liquidation_id','Colocaciones')
    date=fields.Date("Fecha de Negociación",required=True,default=fields.Date.context_today)
    sale_number = fields.Char(string="Venta No.")  # Ejemplo: 10318-VRF45
    current_nominal_value = fields.Monetary(string="Val. Nom. Actual")  # 100.000,00
    original_nominal_value = fields.Monetary(string="Val. Nom. Original")  # 100.000,00
    effective_value = fields.Monetary(string="Valor Efectivo (A)")  # 90.593,20
    price_percentage = fields.Float(string="Precio (%)",digits=(16,8),compute="compute_nominal_value",store=True,readonly=True)  # 90,59320100 %
    nominal_interest_rate = fields.Float(string="Interés Nominal (%)",digits=(16,8))  # 9,000000 %
    tir_tea = fields.Float(string="TIR / TEA(%)",digits=(16,8))  # 12,00550 %
    net_price_percentage = fields.Float(string="Precio Neto (%)",digits=(16,8))  # 89,05912000 %
    day_base = fields.Char(string="Base Días",default="360/360")  # 360/360
    term_to_maturity = fields.Char(string="Plazo por Vencer")  # 5 a. 1800 d.
    issuance = fields.Integer(string="Emisión")
    emisor_id=fields.Many2one('res.partner','Emisor')

    price_net = fields.Float(string="Precio Neto", digits=(16, 8), compute="compute_price_net", store=True,
                                    readonly=True)  # 90,59320100 %

    total_payment=fields.Monetary("Total Pagado",compute="_compute_totals",store=True,readonly=True)
    total_invoiced = fields.Monetary("Total Facturado", compute="_compute_totals", store=True, readonly=True)

    invoice_fsv_id=fields.Many2one("account.move","Servicio")
    invoice_fbv_id = fields.Many2one("account.move","Bolsa de Valores")

    invoice_fsv_invoice_date = fields.Date(related="invoice_fsv_id.invoice_date",store=False,readonly=True,string="Fecha Fact. Servicio")
    invoice_fsv_amount_total = fields.Monetary(related="invoice_fsv_id.amount_total",store=False,readonly=True,string="Total Fact. Servicio")
    invoice_fsv_partner_id = fields.Many2one(related="invoice_fsv_id.partner_id",store=False,readonly=True,string="Proveedor Fact. Servicio")

    invoice_fbv_invoice_date = fields.Date(related="invoice_fbv_id.invoice_date", store=False, readonly=True,string="Fecha FBV")
    invoice_fbv_amount_total = fields.Monetary(related="invoice_fbv_id.amount_total", store=False, readonly=True,string="Total FBV")
    invoice_fbv_partner_id = fields.Many2one(related="invoice_fbv_id.partner_id", store=False, readonly=True,string="Proveedor FBV")

    invoice_fsv_amount_residual = fields.Monetary(related="invoice_fsv_id.amount_residual", store=False, readonly=True,
                                             string="Saldo Fact. Servicio")
    invoice_fbv_amount_residual = fields.Monetary(related="invoice_fbv_id.amount_residual", store=False, readonly=True,
                                                  string="Saldo FBV Servicio")

    reconciled_amount_fsv = fields.Monetary(string="Monto Pagado FSV", compute="_compute_totals", store=True,readonly=True)
    reconciled_amount_fbv = fields.Monetary(string="Monto Pagado FBV", compute="_compute_totals", store=True,readonly=True)

    def _compute_paid_fsv(self):
        for rec in self:
            total = 0.0
            if rec.invoice_fsv_id:
                # Obtenemos las líneas tipo 'receivable' o 'payable'
                lines = rec.invoice_fsv_id.line_ids.filtered(
                    lambda l: l.account_id.account_type in ('liability_payable',)
                )
                for line in lines:
                    for partial in line.matched_debit_ids + line.matched_credit_ids:
                        total += partial.amount
            rec.reconciled_amount_fsv = total

    def _compute_paid_fbv(self):
        for rec in self:
            total = 0.0
            if rec.invoice_fbv_id:
                lines = rec.invoice_fbv_id.line_ids.filtered(
                    lambda l: l.account_id.account_type in ('liability_payable',)
                )
                for line in lines:
                    for partial in line.matched_debit_ids + line.matched_credit_ids:
                        total += partial.amount
            rec.reconciled_amount_fbv = total

    move_payment_ids = fields.Many2many("account.move",string="Pagos",compute="_compute_move_payments",store=False,readonly=True)

    @api.onchange('emisor_id')
    def onchange_emisor_id(self):
        self.invoice_fsv_id=False

    @api.onchange('invoice_fsv_id','invoice_fsv_id.state', 'invoice_fbv_id', 'invoice_fbv_id.state','invoice_fsv_id.amount_residual','invoice_fbv_id.amount_residual'  )
    @api.depends('invoice_fsv_id','invoice_fsv_id.state','invoice_fbv_id', 'invoice_fbv_id.state' ,'invoice_fsv_id.amount_residual','invoice_fbv_id.amount_residual')
    def _compute_totals(self):
        DEC=2
        for brw_each in self:
            brw_each._compute_paid_fsv()
            brw_each._compute_paid_fbv()
            total_payment=brw_each.reconciled_amount_fsv+brw_each.reconciled_amount_fbv
            brw_each.total_invoiced=round(brw_each.invoice_fbv_id.amount_total+brw_each.invoice_fsv_id.amount_total,DEC)
            brw_each.total_payment =round(total_payment,DEC)

    @api.onchange('invoice_fsv_id', 'invoice_fbv_id' )
    @api.depends('invoice_fsv_id', 'invoice_fbv_id' )
    def _compute_move_payments(self):
        for brw_each in self:
            invoices= brw_each.invoice_fsv_id+brw_each.invoice_fbv_id
            move_payments = invoices and invoices.get_applied_moves() or self.env[
                "account.move"]
            brw_each.move_payment_ids = move_payments

    @api.onchange('current_nominal_value','original_nominal_value','effective_value')
    @api.depends('current_nominal_value', 'original_nominal_value', 'effective_value')
    def compute_nominal_value(self):
        for brw_each in self:
            price_percentage=0.00
            if brw_each.current_nominal_value>0.00:
                price_percentage=(brw_each.effective_value/brw_each.current_nominal_value)*100.00
            brw_each.price_percentage=price_percentage

    @api.onchange('current_nominal_value', 'original_nominal_value', 'net_price_percentage')
    @api.depends('current_nominal_value', 'original_nominal_value', 'net_price_percentage')
    def compute_price_net(self):
        DEC=2
        for brw_each in self:
            price_net = 0.00
            if brw_each.current_nominal_value > 0.00:
                price_net = round((brw_each.current_nominal_value * brw_each.net_price_percentage) /100.00,DEC)
            brw_each.price_net = price_net

    @api.onchange('document_id')
    def onchange_document_id(self):
        self.ensure_one()
        lines=self.document_id.line_ids
        placement_ids=[(5,)]
        i=0
        last_date = self.document_id.date_process
        for each_line in lines:
            if each_line.quota>0:
                start_date=last_date
                if i>0:
                    start_date = last_date
                placement_ids.append((0,0,{
                    "type_emission":self.document_id.type_emission,
                    "type_class": self.document_id.type_class,
                    'company_id':self.document_id.company_id,
                    #'company_id': self.document_id.company_id,
                    'document_id':self.document_id.id,
                    'document_line_id': each_line.id,
                    'start_date':start_date,
                    'due_date': each_line.date_process,
                }   ))
                last_date=each_line.date_process
                i+=1
        self.placement_ids=placement_ids

    @api.model
    def create(self, vals):
        record = super().create(vals)
        if vals.get('attachment_ids'):
            attachment_ids = [cmd[1] for cmd in vals['attachment_ids'] if cmd[0] == 4]
            record.update_attachments(added_ids=attachment_ids, removed_ids=[])
        return record

    def write(self, vals):
        old_attachment_ids = set(self.attachment_ids.ids)
        result = super().write(vals)
        if 'attachment_ids' in vals:
            new_attachment_ids = set(self.attachment_ids.ids)
            added_ids = list(new_attachment_ids - old_attachment_ids)
            removed_ids = list(old_attachment_ids - new_attachment_ids)
            self.update_attachments(added_ids=added_ids, removed_ids=removed_ids)
        document_ids = self.mapped('document_id')
        if document_ids:
            document_ids.update_invoices()
            document_ids.action_update_lines()
        return result

    def update_attachments(self, added_ids, removed_ids):
        for record in self:
            for placement in record.placement_ids:
                # Agregar nuevos adjuntos
                for attachment_id in added_ids:
                    placement.document_line_id.attachment_ids = [(4, attachment_id)]
                # Remover adjuntos eliminados
                for attachment_id in removed_ids:
                    placement.document_line_id.attachment_ids = [(3, attachment_id)]

    _rec_name="number_liquidation"

    def action_register_fsv_payment(self):
        self.ensure_one()
        if not self.invoice_fsv_id:
            raise ValidationError(_("Debes definir al menos una factura para realizar esta accion"))
        return self.invoice_fsv_id.action_register_payment()

    def action_register_fbv_payment(self):
        self.ensure_one()
        if not self.invoice_fbv_id:
            raise ValidationError(_("Debes definir al menos una factura para realizar esta accion"))
        return self.invoice_fbv_id.action_register_payment()

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        raise ValidationError(_("No puedes duplicar este documento"))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        document_ids=records.mapped('document_id')
        if document_ids:
            document_ids.action_update_lines()
        return records
