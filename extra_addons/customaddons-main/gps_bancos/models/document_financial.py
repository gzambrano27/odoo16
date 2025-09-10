# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID


class DocumentFinancial(models.Model):

    _name = "document.financial"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Operacion Financiera"

    internal_type=fields.Selection([
        ('out','Pagos'),
        ('in', 'Cobros'),

    ],string="Tipo de Operacion Interna",default="out",tracking=True)

    type=fields.Selection([('pagares','Pagarés'),
                           ('emision', 'Emisión de Obligaciones'),
                           ('prestamo', 'Obligaciones bancarias'),
                           ('contrato','Contrato')
                           ],string="Tipo",default="emision",tracking=True)

    state = fields.Selection([('draft','Preliminar'),
                              ('posted','Publicado'),
                              ('paid', 'Pagado'),
                              ('cancelled','Anulado')], string="Estado", default="draft",tracking=True)

    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company,tracking=True,
    )
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)

    date_negotiation = fields.Date("Fecha de Negociación", required=True, default=fields.Date.today(),tracking=True)
    date_process=fields.Date("Fecha de Emisión",required=True,default=fields.Date.today(),tracking=True)
    date_maturity = fields.Date("Fecha de Vencimiento",tracking=True, required=False, compute="_compute_date_maturity",store=True)

    name=fields.Char("# Documento",tracking=True,required=True)
    number_invoice = fields.Char("# Facturas",tracking=True, required=False)

    partner_id = fields.Many2one(
        "res.partner",
        string="Emisor",
        required=True,
        copy=False,tracking=True
    )

    line_ids = fields.One2many("document.financial.line", "document_id", "Detalle")
    #editable_line_ids = fields.One2many("document.financial.line", "document_id", "Detalle Editable")

    total = fields.Monetary(string="Total",store=True, compute="_compute_total",tracking=True)
    total_to_paid = fields.Monetary(string="Por Aplicar",store=True, compute="_compute_total",tracking=True)
    total_paid = fields.Monetary(string="Aplicado",store=True, compute="_compute_total",tracking=True)
    total_pending = fields.Monetary(string="Pendiente",store=True, compute="_compute_total",tracking=True)

    comments=fields.Text("Comentarios",tracking=True)
    ##############################################################################################
    amount = fields.Monetary("Monto Financiado", default=0.00, tracking=True)

    percentage_interest = fields.Float("% Interés Nominal Anual", default=0.00, digits=(4, 2), tracking=True)
    interest_rate_type = fields.Selection([
        ('fija', 'Fija'),
        ('variable', 'Variable')
    ], string="Tipo de Tasa de Interés")

    percentage_amortize = fields.Float("% Comisión", default=0.00, digits=(4, 2), tracking=True)
    insurance_rate = fields.Float(string="% Seguro de Desgravamen", digits=(5, 2))

    commission_value = fields.Monetary(string="Valor Comisión")
    interest_value = fields.Monetary(string="Valor Intereses")
    insurance_value = fields.Monetary(string="Total Seguro de Desg.")

    first_quota_value = fields.Monetary(string="Valor Primera Cuota")
    total_quotas_value = fields.Monetary(string="Suma Total de Cuotas")
    financial_charge = fields.Monetary(string="Carga Financiera")

    capital = fields.Monetary("Pago de  Capital", default=0.00, tracking=True)
    percentage_interest_quota = fields.Float("% de Interes Cuota", default=0.00, digits=(4, 6), tracking=True)

    ##############################################################################################
    periods = fields.Integer("# Periodos", default=0,tracking=True,compute="_compute_periods")
    years = fields.Integer("Años", default=0,tracking=True,compute="_compute_periods")

    type_document = fields.Selection([('compute', 'Calculado'),
                                      ('file', 'Archivo')], string="Tipo", default="compute",tracking=True)

    invoice_ids = fields.Many2many("account.move", "document_financial_invoice_rel", "document_id", "invoice_id",
                                   "Facturas")

    migrated=fields.Boolean("Documento Migrado",default=False,tracking=True)

    update_lines = fields.Boolean("Tabla de Col.", default=False, tracking=True)

    apply_payment_ids=fields.One2many('document.financial.line.payment',"document_id","Aplicacion de Pagos/Cobros")
    apply_payment_group_ids = fields.One2many('document.financial.line.payment.group', "document_id", "Pagos/Cobros")

    cobro_apply_payment_group_ids = fields.One2many('document.financial.line.payment.group', "document_cobro_id", "Recaudacion")

    type_emission=fields.Selection([('1','Primera Emisión'),
                               ('2','Segunda Emisión'),
                               ('3','Tercera Emisión')],string="Tipo de Emisión",tracking=True)

    type_class = fields.Selection([('A', 'A'),
                                   ('B', 'B'),
                                   ('C', 'C'),
                                   ('D', 'D')], string="Clase",tracking=True)

    full_name = fields.Char(string="Descripción Documento", compute="_compute_full_name",
                                        store=True)

    prestamo_capital_acct_id = fields.Many2one("account.account", "Cuenta Capital Prestamos",tracking=True)

    number_payments = fields.Boolean(string="# Pagos", compute="_compute_numbers",
                                     store=False, readonly=True)
    number_cobros_payments= fields.Boolean(string="# Recaudaciones", compute="_compute_numbers",
                                     store=False, readonly=True)
    total_to_collect = fields.Monetary(string="Total por Recaudar", store=True, compute="_compute_collection_totals",
                                       tracking=True)
    total_collected = fields.Monetary(string="Total Recaudado", store=True, compute="_compute_collection_totals",
                                      tracking=True)
    total_pending_collection = fields.Monetary(string="Total Pendiente de Recaudar", store=True,
                                               compute="_compute_collection_totals", tracking=True)

    account_analytic_id = fields.Many2one('account.analytic.account', 'Proyecto', required=False,tracking=True)

    account_analytic_ids = fields.Many2many('account.analytic.account','doc_financial_account_analytics_rel','document_id','analytic_id', 'Proyectos', required=False, tracking=True)

    name_contract=fields.Char("Nombre de Contrato")

    ubicaciones_id = fields.Many2one(related="account_analytic_id.ubicaciones_id", store=False, readonly=True)
    tipo_proy_id = fields.Many2one(related="account_analytic_id.tipo_proy_id", store=False, readonly=True)
    nro_contrato = fields.Char(related="account_analytic_id.nro_contrato", store=False, readonly=True)

    last_version_id = fields.Many2one('document.financial.version', 'Ult. Versión',tracking=True)
    version=fields.Integer("Versión",default=1,tracking=True)

    placement_ids = fields.One2many('document.financial.placement', 'document_id', 'Colocaciones')
    payment_capital_lines = fields.Monetary("Capital Colocado", default=0.00, required=False, tracking=True,
                                            compute="_compute_placement_lines")
    payment_interest_lines = fields.Monetary("Interés Colocado", default=0.00, required=False, tracking=True,
                                             compute="_compute_placement_lines")
    liquidation_ids=fields.One2many('document.financial.liquidation','document_id','Liquidaciones')

    day_base = fields.Char(string="Base Días", default="360/360")  # 360/360
    term_to_maturity = fields.Char(string="Plazo por Vencer")  # 5 a. 1800 d.

    # ubicaciones_ids = fields.Many2many('res.country.state', string='Ubicaciones', compute='_compute_ubicaciones_ids',
    #                                    store=False)
    # tipo_proy_ids = fields.Many2many('tipo.proyecto', string='Tipos de Proyecto', compute='_compute_tipo_proy_ids',
    #                                  store=False)
    # nro_contratos = fields.Char(string='Nros. de Contrato', compute='_compute_nro_contratos', store=False)
    #
    #
    # @api.depends('account_analytic_ids.ubicaciones_id')
    # def _compute_ubicaciones_ids(self):
    #     for record in self:
    #         ubicaciones = record.account_analytic_ids.mapped('ubicaciones_id')
    #         record.ubicaciones_ids = [(6, 0, ubicaciones.ids)]
    #
    # @api.depends('account_analytic_ids.tipo_proy_id')
    # def _compute_tipo_proy_ids(self):
    #     for record in self:
    #         tipos = record.account_analytic_ids.mapped('tipo_proy_id')
    #         record.tipo_proy_ids = [(6, 0, tipos.ids)]
    #
    # @api.depends('account_analytic_ids.nro_contrato')
    # def _compute_nro_contratos(self):
    #     for record in self:
    #         contratos = record.account_analytic_ids.mapped('nro_contrato')
    #         # Evita valores nulos y concatena por coma
    #         contratos_filtrados = list(filter(None, contratos))
    #           record.nro_contratos = ', '.join(sorted(set(contratos_filtrados)))

    @api.depends('type', 'update_lines', 'placement_ids',
                 'placement_ids.interest_amount', 'placement_ids.principal_amount')
    def _compute_placement_lines(self):
        DEC = 2
        for brw_each in self:
            payment_capital_lines, payment_interest_lines = 0.00, 0.00
            for brw_line in brw_each.placement_ids:
                payment_capital_lines += brw_line.principal_amount
                payment_interest_lines += brw_line.interest_amount
            brw_each.payment_capital_lines = round(payment_capital_lines, DEC)
            brw_each.payment_interest_lines = round(payment_interest_lines, DEC)

    @api.depends('line_ids','line_ids.quota','line_ids.date_process')
    def _compute_periods(self):
        for brw_each in self:
            periods=len(brw_each.line_ids.filtered(lambda x:x.quota>0))
            years={d.year for d in brw_each.line_ids.mapped('date_process') if d}
            brw_each.years=len(years)
            brw_each.periods = periods

    @api.depends('state', 'apply_payment_ids','cobro_apply_payment_group_ids')
    def _compute_numbers(self):
        for brw_each in self:
            payments = set()
            number_cobros_payments=set()
            # Itera una sola vez sobre las líneas
            for line in brw_each.apply_payment_ids:
                if line.payment_id:
                    payments.add(line.payment_id)
            for line in brw_each.cobro_apply_payment_group_ids:
                if line.payment_id:
                    number_cobros_payments.add(line.payment_id)
            brw_each.number_payments = len(payments)
            brw_each.number_cobros_payments=len(number_cobros_payments)

    @api.depends('type', 'name', 'type_emission', 'type_class')
    @api.onchange('type', 'name', 'type_emission', 'type_class')
    def _compute_full_name(self):
        for record in self:
            tipo = dict(self._fields['type'].selection).get(record.type, '')
            emision = dict(self._fields['type_emission'].selection).get(record.type_emission, '')
            clase = record.type_class or ''
            partes = [p for p in [tipo, record.name, emision, f"Clase {clase}" if clase else ''] if p]
            record.full_name = ', '.join(partes)

    _check_company_auto = True

    @api.onchange('type')
    def onchange_type(self):
        if self.type=="emision":
            self.type_emission='1'
            self.type_class='A'
            self.update_lines=True
        else:
            self.update_lines = False

    @api.constrains('total_pending_collection')
    def _check_total_pending_collection(self):
        for record in self:
            if record.total_pending_collection <0.00:
                raise ValidationError("El Total Recaudado no puede ser menor a 0.00")
            if record.total_pending_collection>record.total_to_collect:
                raise ValidationError("El Total Recaudado no puede ser mayor a Total por Recaudar")

    @api.constrains('percentage_amortize', 'percentage_interest', 'percentage_interest_quota')
    def _check_percentages(self):
        for record in self:
            if not (0.00 <= record.percentage_amortize <= 100.00):
                raise ValidationError("El % por Amortizar debe estar entre 0.00 y 100.00.")
            if not (0.00 <= record.percentage_interest <= 100.00):
                raise ValidationError("El % de Interés debe estar entre 0.00 y 100.00.")
            if not (0.00 <= record.percentage_interest_quota <= 100.00):
                raise ValidationError("El % de Interés Cuota debe estar entre 0.00 y 100.00.")

    @api.onchange('invoice_ids')
    def _onchange_invoice_ids(self):
        for record in self:
            if record.invoice_ids:
                names = record.invoice_ids.mapped('name')
                record.number_invoice = ", ".join(names)
            else:
                record.number_invoice = ''

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
            total_paid=sum(brw_pay.payment_id.amount for brw_pay in brw_each.apply_payment_group_ids if not brw_pay.payment_id.reversed_payment_id and brw_pay.payment_id.state=='posted' and not brw_pay.migrated)
            if total_paid!=0.00:
                raise ValidationError(_("No puedes reversar un documento financiero con al menos un valor aplicado"))
            if brw_each.internal_type=='out':
                total_collected=brw_each.total_collected
                if total_collected != 0.00:
                    raise ValidationError(
                        _("No puedes reversar un documento financiero con un valor recaudado mayor a 0.00"))
            brw_each.write({"state":"draft"})
        return True

    def action_cancel(self):
        for brw_each in self:
            total_paid = sum(brw_pay.payment_id.amount for brw_pay in brw_each.apply_payment_group_ids if
                             not brw_pay.payment_id.reversed_payment_id and brw_pay.payment_id.state == 'posted' and not brw_pay.migrated)
            if total_paid != 0.00:
                raise ValidationError(_("No puedes anular un documento financiero con al menos un valor aplicado"))
            brw_each.write({"state":"cancelled"})
        return True

    def unlink(self):
        for brw_each in self:
            if self._context.get("validate_unlink", True):
                if brw_each.state != 'draft':
                    raise ValidationError(_("No puedes borrar un registro que no sea preliminar"))
        return super(DocumentFinancial, self).unlink()

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

    @api.onchange('line_ids','line_ids.total','line_ids.payment_capital','line_ids.payment_interest','line_ids.payment_other',
                  'cobro_apply_payment_group_ids','cobro_apply_payment_group_ids.amount','cobro_apply_payment_group_ids.payment_id','cobro_apply_payment_group_ids.state'
                  )
    def onchange_line_collection_totals(self):
        self.update_collection_totals()

    @api.depends('line_ids','line_ids.total','line_ids.payment_capital','line_ids.payment_interest','line_ids.payment_other',
                  'cobro_apply_payment_group_ids','cobro_apply_payment_group_ids.amount','cobro_apply_payment_group_ids.payment_id','cobro_apply_payment_group_ids.state'
                 )
    def _compute_collection_totals(self):
        for brw_each in self:
            brw_each.update_collection_totals()

    def update_collection_totals(self):
        DEC = 2
        for rec in self:
            total_to_collect,total_collected,total_pending_collection=0.00,0.00,0.00
            if rec.internal_type=='out':
                for brw_line in rec.line_ids:
                    total_to_collect+=(brw_line.payment_capital+brw_line.payment_interest)-brw_line.payment_other
                for brw_payment in rec.cobro_apply_payment_group_ids:
                    if not brw_payment.migrated:
                        if brw_payment.payment_id\
                                and brw_payment.payment_id.state == 'posted'\
                                and not brw_payment.payment_id.reversed_payment_id:
                            total_collected += brw_payment.amount
                    else:
                        total_collected += brw_payment.amount
            total_pending_collection=total_to_collect-total_collected
            rec.total_to_collect = round(total_to_collect,DEC)
            rec.total_collected = round(total_collected,DEC)
            rec.total_pending_collection = round(total_pending_collection,DEC)


    @api.onchange('percentage_amortize')
    def onchange_percentage_amortize(self):
        percentage_amortize=self.percentage_amortize
        if self.percentage_amortize<=0.00:
            self.percentage_amortize=0.00
            return
        brw_lines=self.line_ids
        for brw_line in brw_lines:
            if brw_line.date_process!=self.date_process:
                brw_line.percentage_amortize=percentage_amortize

    @api.onchange('percentage_interest')
    def onchange_percentage_interest(self):
        percentage_interest = self.percentage_interest
        if self.percentage_interest <= 0.00:
            self.percentage_interest = 0.00
            return
        brw_lines = self.line_ids
        for brw_line in brw_lines:
            if brw_line.date_process != self.date_process:
                brw_line.percentage_interest = percentage_interest


    _rec_name="full_name"

    def action_open_payments(self):
        self.ensure_one()
        payments = self.apply_payment_ids.mapped('payment_id')
        payments+= payments.mapped('reversed_payment_id')
        payments_ids = payments.ids + [-1, -1]
        view_ref=self.internal_type =="out" and "account.action_account_payments_payable" or "account.action_account_payments"
        action = self.env["ir.actions.actions"]._for_xml_id(
            view_ref
        )
        action["domain"] = [('id', 'in', payments_ids)]
        print(action)
        return action

    def action_open_cobros_payments(self):
        self.ensure_one()
        payments = self.cobro_apply_payment_group_ids.mapped('payment_id')
        payments+= payments.mapped('reversed_payment_id')
        payments_ids = payments.ids + [-1, -1]
        view_ref="account.action_account_payments"
        action = self.env["ir.actions.actions"]._for_xml_id(
            view_ref
        )
        action["domain"] = [('id', 'in', payments_ids)]
        return action

    def action_financial_version(self):
        self.ensure_one()
        versions = self.env["document.financial.version"].sudo().search([('document_id','=',self.id)])
        versions = versions.ids + [-1, -1]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "gps_bancos.document_financial_version2_view_action"
        )
        action["domain"] = [('id', 'in', versions)]
        return action

    def update_tables(self):
        self.ensure_one()
        context=dict(self.env.context)
        context["default_document_id"]=self.id
        context["default_company_id"] = self.company_id.id
        context["default_type_emission"] = self.type_emission
        context["default_type_class"] = self.type_class
        context["default_start_date"] = self.date_process
        context["default_due_date"] = self.date_process
        context["default_interest_rate"] = self.percentage_interest
        return {
            'type': 'ir.actions.act_window',
            'name': 'Colocaciones Financieras',
            'res_model': 'document.financial.placement',
            'view_mode': 'tree',
            'view_id': self.env.ref('gps_bancos.view_document_financial_placement_tree').id,
            'target': 'current',
            'domain': [ ('document_id','=',self.id)],
            'context': context,
        }

    def update_invoices(self):
        for brw_each in self:
            invoice_ids=self.env["account.move"]
            if brw_each.update_lines:
                invoice_ids=brw_each.liquidation_ids.mapped('invoice_fsv_id')+brw_each.liquidation_ids.mapped('invoice_fbv_id')
            brw_each.invoice_ids=invoice_ids

    def action_update_lines(self):
        DEC=2
        for brw_each in self:
            if brw_each.update_lines:
                lines={}
                for brw_liquidation in brw_each.liquidation_ids:
                    for brw_placement in brw_liquidation.placement_ids:
                        if not lines.get(brw_placement.document_line_id,False):
                            lines[brw_placement.document_line_id]= {
                                "capital":0.00,
                                "interest":0.00
                            }
                        lines[brw_placement.document_line_id]["capital"]+=round(brw_placement.principal_amount,DEC)
                        lines[brw_placement.document_line_id]["interest"] +=round( brw_placement.interest_amount,DEC)
                for brw_line in lines:
                    brw_line.write({
                        "payment_capital":lines[brw_line]["capital"],
                        "payment_interest": lines[brw_line]["interest"]
                    })
        return True

    @api.model
    def action_open_main(self,options, params):
        import re
        match = re.search(r'~([\w\.]+)~(\d+)}?$', self._context.get('active_id',''))
        if match:

            model_name = match.group(1)  # 'document.financial'
            record_id = int(match.group(2))  # 25
            view_id=self.env.ref('gps_bancos.document_financial_view_form').id,
            return {
                'name': "Documento # %s" % (record_id,),
                'view_mode': 'form',
                'res_model': 'document.financial',
                'views': [(view_id, 'form')],
                'type': 'ir.actions.act_window',
                'domain': [],
                'res_id':record_id,
                'context': {},
            }
        return True

class DocumentBank(models.Model):
    _name = "document.bank"

class DocumentBankLine(models.Model):
    _name = "document.bank.line"

class DocumentBankLineInvoiced(models.Model):
    _name = "document.bank.line.invoiced"

class DocumentBankLinePayment(models.Model):
    _name = "document.bank.line.payment"

class DocumentBankLinePaymentGroup(models.Model):
    _name = "document.bank.line.payment.group"