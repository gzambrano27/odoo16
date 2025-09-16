# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID


class DocumentFinancialLine(models.Model):
    _name = "document.financial.line"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Detalle de Operacion Financiera"

    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company,tracking=True
    )
    currency_id = fields.Many2one(related="company_id.currency_id",store=False,readonly=True)


    document_id = fields.Many2one("document.financial", "Documento Bancario", ondelete="cascade")

    partner_id = fields.Many2one(
        "res.partner",
        string="Emisor",
        required=False,
        copy=False, tracking=True,
                             compute="_compute_partner",store=True,readonly=True
    )

    state = fields.Selection([('draft', 'Preliminar'),
                              ('posted', 'Publicado'),
                              ('paid', 'Pagado'),
                              ('cancelled', 'Anulado')], string="Estado", default="draft", tracking=True,
                             compute="_compute_state"
                             )

    quota = fields.Integer(string="Cuota", default=1, required=True,tracking=True)
    date_process = fields.Date("Fecha de Vencimiento", default=fields.Date.today(), required=True,tracking=True)

    date_maturity_payment = fields.Date("Fecha de Prox. Cobro", default=fields.Date.today(), required=True, tracking=True)


    percentage_amortize=fields.Float("% por Amortizar",default=0.00,digits=(16,6),tracking=True)
    percentage_interest=fields.Float("% de Interes",default=0.00,digits=(16,6),tracking=True)

    payment_capital = fields.Monetary("Capital",  default=0.00, required=False,tracking=True)
    payment_interest = fields.Monetary("Interés", default=0.00, required=False,tracking=True)

    payment_overdue_interest = fields.Monetary("Interés Mora", default=0.00, required=False,compute="_compute_total")
    payment_other = fields.Monetary("Otros", default=0.00, required=False,tracking=True)

    amount_interes = fields.Monetary("Interés Generado", default=0.00, tracking=True)
    amount= fields.Monetary("Valor", default=0.00,tracking=True)

    amount_original= fields.Monetary("Valor Original", default=0.00,tracking=True)

    payment_amount_interes = fields.Monetary("Interés Pagado", default=0.00, tracking=True)
    payment_amount = fields.Monetary("Valor Pagado", default=0.00, tracking=True)

    original_amount = fields.Monetary("Valor Original", default=0.00, compute="_compute_amount",store=True,readonly=True,tracking=True)
    total = fields.Monetary("Total", default=0.00,store=True,compute="_compute_total",tracking=True)
    total_to_paid = fields.Monetary("Por Aplicar",  default=0.00, required=False, store=True,compute="_compute_total",tracking=True)
    total_paid = fields.Monetary("Aplicado",  default=0.00, required=False, store=True,compute="_compute_total",tracking=True)
    total_pending = fields.Monetary("Pendiente",  default=0.00, required=False, store=True,compute="_compute_total",tracking=True)

    payment_ids=fields.One2many("document.financial.line.payment","line_id","Pagos")

    version_payment_ids = fields.Many2many("document.financial.line.payment","rel_doc_payment_line_payment","line_id","payment_id","Pagos")

    total_invoiced = fields.Monetary("Facturado", default=0.00, required=False, store=True, compute="_compute_total",tracking=True)
    total_to_invoice = fields.Monetary("Por Facturar", default=0.00, required=False, store=True, compute="_compute_total",tracking=True)

    invoice_ids = fields.One2many("document.financial.line.invoiced", "line_id", "Facturado")

    overdue = fields.Boolean(string="Vencido", compute="_compute_vencido", store=False,readonly=False)

    name=fields.Char(compute="_compute_name",store=True,readonly=False,size=100)

    attachment_ids = fields.Many2many("ir.attachment", "document_financial_line_attch_rel", "document_line_id",
                                      "attachment_id",
                                      "Adjuntos")

    last_version=fields.Integer("Ult. Version",default=True,tracking=True)
    parent_line_id=fields.Many2one('document.financial.line',"Linea Origen",tracking=True)
    version_id=fields.Many2one('document.financial.version','Version',tracking=True)
    is_copy=fields.Boolean('Es una copia',default=False,tracking=True)

    copy_payment_capital = fields.Monetary("Capital Original", default=0.00, required=False,tracking=True)
    copy_payment_interest = fields.Monetary("Interés Original", default=0.00, required=False,tracking=True)

    copy_payment_overdue_interest = fields.Monetary("Interés Mora Original", default=0.00, required=False,tracking=True)
    copy_payment_other = fields.Monetary("Otros Original", default=0.00, required=False,tracking=True)

    copy_paid = fields.Monetary("Pagado Original", default=0.00, required=False,tracking=True)

    comments=fields.Text("Comentarios")

    line_type = fields.Selection(related="document_id.type",store=False,readonly=True)
    update_lines = fields.Boolean(related="document_id.update_lines", store=False, readonly=True)

    payment_capital_lines = fields.Monetary("Capital Colocado", default=0.00, required=False, tracking=True,compute="_compute_placement_lines")
    payment_interest_lines = fields.Monetary("Interés Colocado", default=0.00, required=False, tracking=True,compute="_compute_placement_lines")
    placement_ids=fields.One2many('document.financial.placement','document_line_id','Colocaciones')
    liquidation_ids=fields.Many2many('document.financial.liquidation',string='Liquidaciones',compute="_compute_liquidation_ids")

    amount_iva = fields.Monetary("Valor IVA", default=0.00,store=True, required=False,compute="_compute_total")
    amount_retenido = fields.Monetary("Valor Retenido", default=0.00, store=True, required=False,compute="_compute_total")
    amount_base = fields.Monetary("Valor Base", default=0.00, store=True, required=False,compute="_compute_total")
    amount_total_payments = fields.Monetary("Valor Recaudado", default=0.00, store=True, required=False,
                                  compute="_compute_total")

    @api.depends('document_id', 'document_id.partner_id')
    def _compute_partner(self):
        for brw_each in self:
            partner_id=brw_each.document_id.partner_id
            brw_each.partner_id=partner_id

    @api.depends('placement_ids','placement_ids.liquidation_id')
    def _compute_liquidation_ids(self):
        for brw_each in self:
            liquidation_ids=brw_each.placement_ids.mapped('liquidation_id')
            brw_each.liquidation_ids=liquidation_ids

    @api.depends('document_id.type', 'document_id.update_lines','placement_ids',
                    'placement_ids.interest_amount','placement_ids.principal_amount')
    def _compute_placement_lines(self):
        DEC=2
        for brw_each in self:
            payment_capital_lines,payment_interest_lines=0.00,0.00
            for brw_line in brw_each.placement_ids:
                payment_capital_lines+=brw_line.principal_amount
                payment_interest_lines += brw_line.interest_amount
            brw_each.payment_capital_lines = round(payment_capital_lines,DEC)
            brw_each.payment_interest_lines = round(payment_interest_lines,DEC)

    @api.depends('document_id.state', 'version_id.document_id.state')
    def _compute_state(self):
        for brw_each in self:
            state='draft'
            if brw_each.document_id:
                state=brw_each.document_id.state
            else:
                if brw_each.version_id.document_id:
                    state = brw_each.version_id.document_id.state
            brw_each.state=state

    @api.depends('document_id','quota','date_process')
    def _compute_name(self):
        for brw_each in self:
            doc_number = brw_each.document_id.name if brw_each.document_id else "SIN DOCUMENTO"
            cuota = brw_each.quota or 0
            fecha = brw_each.date_process.strftime("%Y-%m-%d") if brw_each.date_process else "SIN FECHA"
            brw_each.name = f"{doc_number}, CUOTA {cuota}, VENC. {fecha}"

    @api.depends('document_id.state','date_process', 'total_pending')
    def _compute_vencido(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.overdue = bool(record.date_process and record.date_process < today and record.total_pending > 0)

    @api.depends('payment_capital', 'payment_interest','payment_other')
    def _compute_amount(self):
        DEC=2
        for brw_each in self:
            brw_each.original_amount = round(
                brw_each.payment_capital + brw_each.payment_interest  +   brw_each.payment_other,
                DEC)

    @api.depends('document_id.state',
                 'payment_capital', 'payment_interest', 'payment_other',
                 'payment_ids','payment_ids.payment_capital','payment_ids.payment_interest','payment_ids.payment_other','payment_ids.payment_overdue_interest',
                  'payment_ids.payment_id','payment_ids.payment_id.state',
                 'payment_ids.payment_id.reversed_payment_id',
                 'payment_ids.state','payment_ids.payment_group_id.state',
                 'is_copy','copy_payment_capital','copy_payment_interest','copy_payment_overdue_interest','copy_payment_other','copy_paid',
                 'invoice_ids','invoice_ids.state','invoice_ids.invoice_date', 'invoice_ids', 'invoice_ids.amount'
                 )
    @api.onchange('document_id.state',
                 'payment_capital', 'payment_interest', 'payment_other',
                 'payment_ids', 'payment_ids.payment_capital', 'payment_ids.payment_interest',
                 'payment_ids.payment_other', 'payment_ids.payment_overdue_interest',
                  'payment_ids.payment_id','payment_ids.payment_id.state',
                  'payment_ids.payment_id.reversed_payment_id',
                  'payment_ids.state','payment_ids.payment_group_id.state',
                 'is_copy','copy_payment_capital','copy_payment_interest',
                  'copy_payment_overdue_interest','copy_payment_other','copy_paid',
                  'invoice_ids','invoice_ids.state','invoice_ids.invoice_date', 'invoice_ids', 'invoice_ids.amount'
                  )
    def _compute_total(self):
        for brw_each in self:
            brw_each.update_total()

    def update_total(self):
        DEC = 2
        for brw_each in self:
            brw_each.update_invoiced_total()
            amount_iva = 0.00
            amount_retenido = 0.00
            amount_base = 0.00
            amount_total_payments = 0.00

            total = brw_each.amount+brw_each.amount_interes

            if brw_each.is_copy:
                total = round(
                    brw_each.copy_payment_capital + brw_each.copy_payment_interest + brw_each.copy_payment_other,
                    DEC)
            else:
                if brw_each.document_id.internal_type=='out':#
                    total=round(   brw_each.payment_capital + brw_each.payment_interest  +   brw_each.payment_other, DEC)
            total_paid = 0.00
            payment_overdue_interest=0.00
            payment_amount=0.00
            payment_amount_interes=0.00
            if brw_each.is_copy:
                total_paid += brw_each.copy_paid
                payment_overdue_interest += brw_each.copy_payment_overdue_interest
            else:
                if brw_each.document_id.state not in ("draft", "cancelled"):  # paid,#approved
                    if brw_each.document_id.internal_type == 'out':  #
                        for brw_line in brw_each.payment_ids:
                            if not brw_line.migrated:
                                 if brw_line.payment_id and brw_line.payment_id.state == 'posted' and not brw_line.payment_id.reversed_payment_id:
                                    total_paid += brw_line.payment_capital+brw_line.payment_interest+brw_line.payment_overdue_interest+brw_line.payment_other
                                    payment_overdue_interest += brw_line.payment_overdue_interest
                            else:
                                if brw_line.state=='validated':
                                    total_paid +=brw_line.amount
                                    payment_overdue_interest+=brw_line.payment_overdue_interest
                    else:#cobros
                        for brw_line in brw_each.payment_ids:
                            if not brw_line.migrated:
                                if brw_line.payment_id and brw_line.payment_id.state == 'posted' and not brw_line.payment_id.reversed_payment_id:
                                    total_paid += brw_line.payment_amount+brw_line.payment_interes_generado
                                    payment_amount+=brw_line.payment_amount
                                    payment_amount_interes += brw_line.payment_interes_generado

                            else:
                                if brw_line.state == 'validated':
                                    total_paid +=brw_line.payment_amount+brw_line.payment_interes_generado
                                    payment_amount += brw_line.payment_amount
                                    payment_amount_interes += brw_line.payment_interes_generado
                        ################################################################
                        if brw_each.invoice_ids:
                            for brw_line in brw_each.invoice_ids:
                                if brw_line.invoice_id and brw_line.invoice_id.state == 'posted':
                                    amount_iva += brw_line.amount_iva
                                    amount_retenido += brw_line.amount_retenido
                                    amount_base += brw_line.amount_base
                            total_paid += amount_retenido
                        payment_amount += amount_retenido
                        amount_total_payments += payment_amount #+ amount_retenido  # +amount_iva
                        ################################################################


            total=total+payment_overdue_interest+amount_iva#se suma a los interese e valor por pagar
            total_to_paid = total  # siempre tomara el valor a pagar como reflejo de lo que debera pagar

            brw_each.amount_iva = round(amount_iva, DEC)
            brw_each.amount_base = round(amount_base, DEC)
            brw_each.amount_retenido = round(amount_retenido, DEC)
            brw_each.amount_total_payments = round(amount_total_payments, DEC)

            brw_each.total = round(total, DEC)
            brw_each.total_to_paid = round(total_to_paid, DEC)
            brw_each.total_paid = round(total_paid, DEC)
            brw_each.total_pending = round(total_to_paid - total_paid, DEC)
            brw_each.payment_overdue_interest=round(payment_overdue_interest,DEC)

            brw_each.payment_amount =round( payment_amount,DEC)
            brw_each.payment_amount_interes =round( payment_amount_interes,DEC)



    # @api.depends('document_id.state', 'total',
    #              'invoice_ids.state','invoice_ids.invoice_date', 'invoice_ids', 'invoice_ids.amount' )
    # @api.onchange('document_id.state', 'total',
    #               'invoice_ids.state','invoice_ids.invoice_date', 'invoice_ids', 'invoice_ids.amount' )
    def _compute_total_invoice(self):
        for brw_each in self:
            brw_each.update_invoiced_total()

    def update_invoiced_total(self):
        DEC = 2
        for brw_each in self:
            total_invoiced = 0.00
            total_to_invoice = 0.00
            amount_iva = 0.00
            if brw_each.document_id.internal_type!='out':
                total=brw_each.total
                if brw_each.document_id.state not in ("draft", "cancelled"):  # paid,#approved
                    for brw_line in brw_each.invoice_ids:
                        if brw_line.invoice_id and brw_line.invoice_id.state=='posted':
                            total_invoiced += brw_line.amount+brw_line.amount_iva
                            amount_iva+=brw_line.amount_iva
                total_to_invoice=total-total_invoiced
            brw_each.total_invoiced = round(total_invoiced, DEC)
            brw_each.total_to_invoice = round(total_to_invoice, DEC)


    _order="quota asc"

    def unlink(self):
        for brw_each in self:
            if self._context.get("validate_unlink", True):
                if brw_each.state != 'draft':
                    raise ValidationError(_("No puedes borrar un registro que no sea preliminar"))
        return super(DocumentFinancialLine, self).unlink()

    def copy_financial_line(self):
        self.ensure_one()  # Solo uno a la vez
        version_payment_ids=self.payment_ids
        values = {
            'company_id': self.document_id.company_id.id,
            #'document_id': self.document_id.id,
            'quota': self.quota,
            'date_process': self.date_process,
            'percentage_amortize': self.percentage_amortize,
            'percentage_interest': self.percentage_interest,
            'payment_capital': self.payment_capital,
            'payment_interest': self.payment_interest,
            #'payment_overdue_interest': self.payment_overdue_interest,
            'payment_other': self.payment_other,
            'amount': self.amount,
            'original_amount': self.original_amount,
            #'total': self.total,
            #'total_to_paid': self.total_to_paid,
            #'total_paid': self.total_paid,
            #'total_pending': self.total_pending,
            #'total_invoiced': self.total_invoiced,
            #'total_to_invoice': self.total_to_invoice,
            #'overdue': self.overdue,
            #'name': self.name,
            'last_version': False,
            'parent_line_id': self.id,  # Enlace al original
            'version_id': self.version_id.id,
            'is_copy': True,
            'copy_payment_capital': self.payment_capital,
            'copy_payment_interest': self.payment_interest,
            'copy_payment_overdue_interest': self.payment_overdue_interest,
            'copy_payment_other': self.payment_other,
            'copy_paid': self.total_paid,
            'attachment_ids': [(6, 0, self.attachment_ids.ids)],
            "version_payment_ids": [(6, 0, version_payment_ids and version_payment_ids.ids or [] )],
        }
        return values

    def update_tables(self):
        self.ensure_one()
        context=dict(self.env.context)
        context["default_document_id"]=self.document_id.id
        context["default_company_id"] = self.company_id.id
        context["default_quota"] = self.quota
        context["default_type_emission"] = self.document_id.type_emission
        context["default_type_class"] = self.document_id.type_class
        context["default_start_date"] = self.date_process
        context["default_due_date"] = self.date_process
        context["default_interest_rate"] = self.percentage_interest
        context["hide_quota"]=True
        context["default_document_line_id"] = self.id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Colocaciones Financieras',
            'res_model': 'document.financial.placement',
            'view_mode': 'tree',
            'view_id': self.env.ref('gps_bancos.view_document_financial_placement_tree').id,
            'target': 'current',
            'domain': [('document_line_id','=',self.id),('document_id','=',self.document_id.id)],
            'context': context,
        }

