# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from werkzeug.filesystem import BrokenFilesystemWarning
from xlrd import open_workbook
from odoo.exceptions import ValidationError
from ...calendar_days.tools import CalendarManager,DateManager
from ...message_dialog.tools import FileManager
dtObj=DateManager()
clObj=CalendarManager()
flObj=FileManager()

from dateutil.relativedelta import relativedelta

class DocumentFinancialWizard(models.Model):
    _name = "document.financial.wizard"
    _description = "Asistente de Operacion Financiera"

    @api.model
    def _get_default_bank_id(self):
        if self._context.get('active_model','')=='document.financial':
            return self._context.get("active_ids") and self._context.get("active_ids")[0] or False
        brw_lines=self.env["document.financial.line"].sudo().browse(self._context.get("active_ids"))
        return brw_lines.document_id.id

    @api.model
    def _get_default_line_ids(self):
        if self._context.get('active_model', '') == 'document.financial.line':
            return [(6,0,self._context.get("active_ids",[]) )]
        return []

    @api.model
    def _get_default_financial_line_ids(self):
        if self._context.get('active_model', '') == 'document.financial.line':
            return [(6, 0, self._context.get("active_ids", []))]
        return []

    @api.model
    def _default_apply_invoice_ids(self):
        if self._context.get('active_model', '') == 'document.financial':
            brw_document=self.env["document.financial"].sudo().browse(self._context.get("active_ids"))
            invoice_ids=brw_document.line_ids.mapped('invoice_ids').mapped('invoice_id')
            return invoice_ids and invoice_ids.ids or []
        if self._context.get('active_model', '') == 'document.financial.line':
            brw_document_line = self.env["document.financial.line"].sudo().browse(self._context.get("active_ids"))
            invoice_ids = brw_document_line.mapped('document_id').line_ids.mapped('invoice_ids').mapped('invoice_id')
            return invoice_ids and invoice_ids.ids or []
        return []

    @api.model
    def _get_default_name(self):
        name = self.env["ir.sequence"].sudo().next_by_code("document.financial.ref.sequence")
        return name

    document_financial_id=fields.Many2one("document.financial","Documento",ondelete="cascade",default=_get_default_bank_id)

    document_financial_type = fields.Selection(related="document_financial_id.type",string="Documento Tipo",store=False,readonly=True)

    internal_type = fields.Selection(related="document_financial_id.internal_type",store=False,readonly=True)

    company_id=fields.Many2one(related="document_financial_id.company_id",store=False,readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)
    partner_id = fields.Many2one(related="document_financial_id.partner_id", store=False, readonly=True)

    type_action=fields.Selection([('import','Importado'),   ('process','Procesar')],string="Tipo de Accion",
                                 default="import")

    type=fields.Selection([('compute','Calculado'),
                           ('file','Archivo')],string="Tipo",default="file")

    message=fields.Text("Comentarios")
    amount=fields.Monetary("Valor Nominal",default=0.01)
    percentage_amortize=fields.Float("% por Amortizar",default=0.00,digits=(4,2),compute="compute_capital")
    percentage_type=fields.Selection([('fixed','Fijo')],string="Tipo de % de Interes",default="fixed")
    percentage_interest=fields.Float("% de Interes",default=2.25,digits=(4,2))
    percentage_interest_quota=fields.Float("% de Interes Cuota",default=0.00,digits=(4,6))
    capital = fields.Monetary("Pago de  Capital",default=0.00,compute="compute_capital")
    periods = fields.Integer("# Periodos", default=0, compute="compute_capital")
    years=fields.Integer("Años",default=5)

    file = fields.Binary("Archivo", required=False, filters='*.xlsx')
    file_name = fields.Char("Nombre de Archivo", required=False, size=255)

    line_ids=fields.Many2many("document.financial.line","document_financial_wizard_line_rel","wizard_id","bank_line_id","Detalles",default=_get_default_line_ids)

    payment_amount=fields.Monetary("Monto de Pago",required=True,default=0.01)
    payment_date = fields.Date("Fecha de Pago", required=True, default=fields.Date.today())

    payment_capital = fields.Monetary("Capital", default=0.00, required=False)
    payment_interest = fields.Monetary("Interés", default=0.00, required=False)
    payment_overdue_interest = fields.Monetary("Interés Mora", default=0.00, required=False)
    payment_other = fields.Monetary("Otros", default=0.00, required=False)

    original_payment_capital = fields.Monetary("Saldo Capital", default=0.00, required=False)
    original_payment_interest = fields.Monetary("Saldo Interés", default=0.00, required=False)
    original_payment_other = fields.Monetary("Saldo Otros", default=0.00, required=False)

    original_payment_capital_sinaplicar = fields.Monetary("Capital sin Aplicar", default=0.00, required=False)
    original_payment_interest_sinaplicar = fields.Monetary("Interés sin Aplicar", default=0.00, required=False)
    original_payment_other_sinaplicar = fields.Monetary("Otros sin Aplicar", default=0.00, required=False)

    #####################################################################################
    payment_cobro_amount = fields.Monetary("Cobro Valor", default=0.00, required=False)
    payment_cobro_interes = fields.Monetary("Cobro Interés", default=0.00, required=False)

    original_cobro_amount = fields.Monetary("Cobro Saldo", default=0.00, required=False)
    original_cobro_interes = fields.Monetary("Cobro Saldo Interés", default=0.00, required=False)

    original_cobro_amount_sinaplicar = fields.Monetary("Cobro Valor sin Aplicar", default=0.00, required=False)
    original_cobro_interes_sinaplicar = fields.Monetary("Cobro Interés sin Aplicar", default=0.00, required=False)

    #####################################################################################
    payment_total = fields.Monetary("Saldo", default=0.00, required=False,store=True)

    invoice_ids = fields.Many2many("account.move", "document_financial_wizard_invoice_rel", "wizard_id", "invoice_id",
                                "Facturas")

    attachment_ids = fields.Many2many("ir.attachment", "document_financial_wizard_attachment_rel", "wizard_id", "attachment_id",
                                   "Adjuntos")
    ref = fields.Char("# Referencia", default=None, size=255, required=False)

    journal_id=fields.Many2one('account.journal','Diario',required=False)

    line_account_ids=fields.One2many('document.financial.line.wizard','wizard_id',"Detalle de Cuentas")

    do_account=fields.Boolean("Contabilizar",default=True)

    name = fields.Char("# Documento",   size=32, required=True,default=_get_default_name)

    payment_amount_income = fields.Monetary("Saldo ", default=0.00, required=False, compute="_compute_income_total")

    payment_amount_collect = fields.Monetary("Saldo", default=0.00, required=False, compute="_compute_collect_total")
    payment_collect = fields.Monetary("Monto por Recaudar", default=0.00, required=False )

    is_cobro=fields.Boolean('Es recaudacion?',default=False)
    register_invoices=fields.Boolean('Registrar Facturas?',default=False)

    financial_line_ids=fields.Many2many('document.financial.line','doc_financial_wizard_line_rel','wizard_id','line_id','Cuotas',default=_get_default_financial_line_ids)
    invoiced_line_ids=fields.One2many('document.financial.line.invoiced.wizard','wizard_id','Facturado')

    apply_invoice_ids=fields.Many2many('account.move','financial_wizard_invoice_rel','wizard_id','invoice_id','Facturas Aplicadas',default=_default_apply_invoice_ids)

    @api.constrains('payment_capital', 'payment_interest', 'payment_other','original_payment_capital','original_payment_interest','original_payment_other')
    @api.onchange('payment_capital', 'payment_interest', 'payment_other','original_payment_capital','original_payment_interest','original_payment_other')
    def _check_payment_not_exceed_original(self):
        for record in self:
            if record.payment_capital > record.original_payment_capital:
                pass#raise ValidationError("El capital ingresado no puede ser mayor al capital original.")
            if record.payment_interest > record.original_payment_interest:
                pass#raise ValidationError("El interés ingresado no puede ser mayor al interés original.")
            if record.payment_other > record.original_payment_other:
                pass#raise ValidationError("El valor de 'Otros' no puede ser mayor al valor original.")

    @api.onchange('payment_capital','payment_interest','payment_overdue_interest','payment_other','payment_amount_income')
    @api.depends('payment_capital', 'payment_interest', 'payment_overdue_interest', 'payment_other','payment_amount_income')
    def _compute_total(self):
        DEC=2
        for brw_each in self:

            payment_total=round(brw_each.payment_capital+\
                                brw_each.payment_interest+\
                                brw_each.payment_overdue_interest+\
                                brw_each.payment_other,DEC)
            if brw_each.internal_type=='in':
                payment_total=brw_each.payment_amount_income
            brw_each.payment_total=payment_total

    @api.onchange('payment_cobro_amount', 'payment_cobro_interes','internal_type')
    @api.depends('payment_cobro_amount', 'payment_cobro_interes','internal_type')
    def _compute_income_total(self):
        DEC = 2
        for brw_each in self:
            payment_amount_income = 0.00
            if brw_each.internal_type=='in':
                payment_amount_income = round(brw_each.payment_cobro_amount + brw_each.payment_cobro_interes, DEC)
            brw_each.payment_amount_income = payment_amount_income

    @api.constrains('payment_cobro_amount', 'payment_cobro_interes','original_cobro_amount', 'original_cobro_interes' )
    @api.onchange('payment_cobro_amount', 'payment_cobro_interes','original_cobro_amount', 'original_cobro_interes' )
    def _check_payment_not_exceed_cobro_original(self):
        for record in self:
            pass
            # if record.payment_cobro_amount > record.original_cobro_amount:
            #      raise ValidationError("El monto ingresado no puede ser mayor al monto original.")
            # if record.payment_cobro_amount > record.original_cobro_amount:
            #      raise ValidationError("El interés ingresado no puede ser mayor al interés original.")


    @api.onchange('document_financial_id', 'document_financial_id.total_pending_collection')
    @api.depends('document_financial_id', 'document_financial_id.total_pending_collection')
    def _compute_collect_total(self):
        DEC = 2
        for brw_each in self:
            payment_amount_collect = round(brw_each.document_financial_id.total_pending_collection, DEC)
            brw_each.payment_amount_collect = payment_amount_collect



    @api.onchange('payment_amount_collect')
    def _onchange_payment_amount_collect(self):
        for brw_each in self:
            brw_each.payment_collect = brw_each.payment_amount_collect

    @api.onchange('is_cobro','line_ids',
                  'payment_total','payment_capital','payment_interest',
                  'payment_other','payment_overdue_interest','journal_id','payment_collect',
                  'payment_cobro_amount','payment_cobro_interes'
                  )
    def onchange_line_account_ids(self):
        if self.document_financial_id.type=="emision":
            if not  self.is_cobro:
                self.update_by_emision_account_ids()
            else:
                self.update_by_recaudacion_account_ids()
        if self.document_financial_id.type=="prestamo":
            if not self.is_cobro:
                self.update_by_prestamo_account_ids()
            else:
                self.update_by_recaudacion_account_ids()
        if self.document_financial_id.type=="contrato":
            self.update_by_contrato_account_ids()

    def _get_property_account_receivable_id(self):
        self.ensure_one()
        if self.document_financial_id.type!='emision':
            return self.document_financial_id.prestamo_capital_acct_id and self.document_financial_id.prestamo_capital_acct_id or False
        brw_conf = self.document_financial_id.company_id.get_payment_conf()
        dscr_payment = ""
        account_id = False
        if self.document_financial_id.type_emission == '1':
            dscr_payment = "Primera"
            account_id = brw_conf.first_bond_issuance_acct_id
        elif self.document_financial_id.type_emission == '2':
            dscr_payment = "Segunda"
            account_id = brw_conf.second_bond_issuance_acct_id
        elif self.document_financial_id.type_emission == '3':
            dscr_payment = "Tercera"
            account_id = brw_conf.third_bond_issuance_acct_id
        if not account_id:
            raise ValidationError(_("No hay Cuenta para %s Obligacion configurada") % (dscr_payment,))
        return account_id

    def update_by_recaudacion_account_ids(self):
        line_account_ids = [(5,)]
        DEC = 2
        if self.payment_collect > 0.00:
            payment_collect = round(self.payment_collect, DEC)  ##EL INTERES se resta
            if payment_collect > 0.00:
                account_id = self._get_property_account_receivable_id()
                if not account_id:
                    raise ValidationError(_("No hay Cuenta configurada para Cuentas por Cobrar "))
                line_account_ids.append((0, 0, {
                    "account_id": account_id and account_id.id or False,
                    #"partner_id": self.document_financial_id.partner_id.id,
                    "debit": 0.00,
                    "credit": payment_collect
                }))

            account_payment_method_manual_in = self.env.ref('account.account_payment_method_manual_in').id
            outbound_payment_account_line = self.journal_id.outbound_payment_method_line_ids.filtered(
                lambda line: line.payment_method_id == account_payment_method_manual_in
            )
            bank_account_id = outbound_payment_account_line.payment_account_id and outbound_payment_account_line.payment_account_id.id or self.journal_id.default_account_id.id
            line_account_ids.append((0, 0, {
                "account_id": bank_account_id,
                #"partner_id": self.document_financial_id.partner_id.id,
                "debit": payment_collect,
                "credit": 0.00,
            }))
        self.line_account_ids = line_account_ids

    def update_by_prestamo_account_ids(self):
        line_account_ids = [(5,)]
        DEC = 2
        brw_conf = self.document_financial_id.company_id.get_payment_conf()
        payment_total = round(
            self.payment_capital + self.payment_interest + self.payment_overdue_interest + self.payment_other, DEC)
        if payment_total > 0.00 and brw_conf:
            payment_total = 0.00

            payment_capital = round(self.payment_capital, DEC)  ##EL INTERES se resta
            if payment_capital > 0.00:
                payment_total+=payment_capital
                account_id = self.document_financial_id.prestamo_capital_acct_id
                if not account_id:
                    raise ValidationError(_("No hay Cuenta Capital Prestamos configurada")  )
                line_account_ids.append((0, 0, {
                    "account_id": account_id and account_id.id or False,
                    #"partner_id": self.document_financial_id.partner_id.id,
                    "debit": payment_capital,
                    "credit": 0.00
                }))

            payment_interest = round(self.payment_interest, DEC)  ##EL INTERES se resta
            if payment_interest > 0.00:
                payment_total += payment_interest
                account_id = brw_conf.prestamo_interes_acct_id
                if not account_id:
                    raise ValidationError(_("No hay Cuenta para Cuenta Interes Prestamos configurada"))
                line_account_ids.append((0, 0, {
                    "account_id": account_id and account_id.id or False,
                    #"partner_id": self.document_financial_id.partner_id.id,
                    "debit": payment_interest,
                    "credit": 0.00
                }))

            payment_overdue_interest = round(self.payment_overdue_interest, DEC)
            if payment_overdue_interest > 0.00:
                payment_total += payment_overdue_interest
                account_id = brw_conf.prestamo_interes_mora_acct_id and brw_conf.prestamo_interes_mora_acct_id.id or False
                if not account_id:
                    raise ValidationError(_("No hay Cuenta para Interés Mora"))
                line_account_ids.append((0, 0, {
                    "account_id": account_id,
                    #"partner_id": self.document_financial_id.partner_id.id,
                    "debit": payment_overdue_interest,
                    "credit": 0.00
                }))

            payment_other = round(self.payment_other, DEC)
            if payment_other > 0.00:
                payment_total += payment_other
                account_id = brw_conf.prestamo_otros_acct_id and brw_conf.prestamo_otros_acct_id.id or False
                if not account_id:
                    raise ValidationError(_("No hay Cuenta Otros Gastos"))
                line_account_ids.append((0, 0, {
                    "account_id": account_id,
                    #"partner_id": self.document_financial_id.partner_id.id,
                    "debit": payment_other,
                    "credit": 0.00
                }))
            payment_total = round(payment_total,DEC)
            account_payment_method_manual_out = self.env.ref('account.account_payment_method_manual_out').id
            outbound_payment_account_line = self.journal_id.outbound_payment_method_line_ids.filtered(
                lambda line: line.payment_method_id == account_payment_method_manual_out
            )
            bank_account_id = outbound_payment_account_line.payment_account_id and outbound_payment_account_line.payment_account_id.id or self.journal_id.default_account_id.id
            line_account_ids.append((0, 0, {
                "account_id": bank_account_id,
                #"partner_id": self.document_financial_id.partner_id.id,
                "debit": 0.00,
                "credit": payment_total
            }))
        self.line_account_ids = line_account_ids

    def update_by_emision_account_ids(self):
        line_account_ids = [(5,)]
        DEC = 2
        brw_conf = self.document_financial_id.company_id.get_payment_conf()
        payment_total=round(self.payment_capital+self.payment_interest+self.payment_overdue_interest+self.payment_other, DEC)
        if payment_total > 0.00 and brw_conf:
            payment_total=0.00
            type_emission_field = self.document_financial_id._fields['type_emission']
            selection_dict = dict(type_emission_field.selection)
            dscr_payment = selection_dict.get(self.document_financial_id.type_emission, '')

            payment_capital = round(self.payment_capital, DEC)  ##EL INTERES se resta
            if payment_capital > 0.00:
                payment_total+=payment_capital
                dscr_payment = ""
                account_id = False
                if self.document_financial_id.type_emission == '1':
                    dscr_payment = "Primera"
                    account_id = brw_conf.first_bond_issuance_acct_id
                elif self.document_financial_id.type_emission == '2':
                    dscr_payment = "Segunda"
                    account_id = brw_conf.second_bond_issuance_acct_id
                elif self.document_financial_id.type_emission == '3':
                    dscr_payment = "Tercera"
                    account_id = brw_conf.third_bond_issuance_acct_id
                if not account_id:
                        raise ValidationError(_("No hay Cuenta para %s Obligacion configurada") % (dscr_payment,))
                line_account_ids.append((0, 0, {
                    "account_id": account_id and account_id.id or False,
                    #"partner_id": self.document_financial_id.partner_id.id,
                    "debit": payment_capital,
                    "credit": 0.00
                }))

            payment_interest = round(self.payment_interest, DEC)  ##EL INTERES se resta

            if payment_interest > 0.00:
                payment_total += payment_interest
                dscr_payment = ""
                account_id = False
                if self.document_financial_id.type_emission == '1':
                    dscr_payment = "Primera"
                    account_id = brw_conf.int_first_bond_issuance_acct_id
                elif self.document_financial_id.type_emission == '2':
                    dscr_payment = "Segunda"
                    account_id = brw_conf.int_second_bond_issuance_acct_id
                elif self.document_financial_id.type_emission == '3':
                    dscr_payment = "Tercera"
                    account_id = brw_conf.int_third_bond_issuance_acct_id
                if not account_id:
                    raise ValidationError(_("No hay Cuenta para Interés %s Obligacion configurada") % (dscr_payment,))
                line_account_ids.append((0, 0, {
                    "account_id": account_id and account_id.id or False,
                    #"partner_id": self.document_financial_id.partner_id.id,
                    "debit": payment_interest,
                    "credit": 0.00
                }))

            payment_overdue_interest = round(self.payment_overdue_interest, DEC)
            if payment_overdue_interest > 0.00:
                payment_total += payment_overdue_interest
                account_id = brw_conf.payment_overdue_interest_acct_id and brw_conf.payment_overdue_interest_acct_id.id or False
                if not account_id:
                    raise ValidationError(_("No hay Cuenta para Interés Mora"))
                line_account_ids.append((0, 0, {
                    "account_id": account_id,
                    #"partner_id": self.document_financial_id.partner_id.id,
                    "debit": payment_overdue_interest,
                    "credit": 0.00
                }))

            payment_other = round(self.payment_other, DEC)
            if payment_other > 0.00:
                payment_total += payment_other
                account_id = brw_conf.payment_other_acct_id and brw_conf.payment_other_acct_id.id or False
                if not account_id:
                    raise ValidationError(_("No hay Cuenta Otros Gastos"))
                line_account_ids.append((0, 0, {
                    "account_id": account_id,
                    #"partner_id": self.document_financial_id.partner_id.id,
                    "debit": payment_other,
                    "credit": 0.00
                }))
            payment_total = round(payment_total,DEC)
            account_payment_method_manual_out=self.env.ref('account.account_payment_method_manual_out').id
            outbound_payment_account_line = self.journal_id.outbound_payment_method_line_ids.filtered(
                lambda line: line.payment_method_id == account_payment_method_manual_out
            )
            bank_account_id = outbound_payment_account_line.payment_account_id and outbound_payment_account_line.payment_account_id.id or self.journal_id.default_account_id.id
            line_account_ids.append((0, 0, {
                "account_id": bank_account_id,
                #"partner_id": self.document_financial_id.partner_id.id,
                "debit": 0.00,
                "credit": payment_total
            }))
        self.line_account_ids = line_account_ids

    def update_by_contrato_account_ids(self):
        line_account_ids = [(5,)]
        DEC = 2
        total=self.payment_cobro_amount+self.payment_cobro_interes
        if total > 0.00:
            payment_total = round(total, DEC)  ##EL INTERES se resta
            if payment_total > 0.00:
                account_id = self.document_financial_id.partner_id.property_account_receivable_id
                if not account_id:
                    raise ValidationError(_("No hay Cuenta configurada para Cuentas por Cobrar "))
                if self.payment_cobro_amount>0:
                    line_account_ids.append((0, 0, {
                        "account_id": account_id and account_id.id or False,
                        #"partner_id": self.document_financial_id.partner_id.id,
                        "debit": 0.00,
                        "credit": self.payment_cobro_amount,
                    }))
                #############################################################################
                if self.payment_cobro_interes > 0:
                    line_account_ids.append((0, 0, {
                        "account_id": account_id and account_id.id or False,
                        # "partner_id": self.document_financial_id.partner_id.id,
                        "debit": 0.00,
                        "credit": self.payment_cobro_interes,
                    }))
            account_payment_method_manual_in = self.env.ref('account.account_payment_method_manual_in').id
            outbound_payment_account_line = self.journal_id.outbound_payment_method_line_ids.filtered(
                lambda line: line.payment_method_id == account_payment_method_manual_in
            )
            bank_account_id = outbound_payment_account_line.payment_account_id and outbound_payment_account_line.payment_account_id.id or self.journal_id.default_account_id.id
            line_account_ids.append((0, 0, {
                "account_id": bank_account_id,
                #"partner_id": self.document_financial_id.partner_id.id,
                "debit":payment_total,
                "credit":  0.00,
            }))
        self.line_account_ids = line_account_ids

    @api.onchange('percentage_interest','years','periods')
    def  onchange_percentage_interest(self):
        percentage_interest_quota = 0.00
        if self.periods>0:
            percentage_interest_quota=round(self.percentage_interest / float(self.periods), 6)  # cuota abajo
        self.percentage_interest_quota=percentage_interest_quota

    @api.onchange('line_ids')
    def onchange_line_ids(self):
        DEC=2
        payment_capital=0.00
        payment_interest = 0.00
        payment_other=0.00
        payment_capital_done = 0.00
        payment_interest_done = 0.00
        payment_other_done = 0.00
        original_payment_capital_sinaplicar=0.00
        original_payment_interest_sinaplicar=0.00
        original_payment_other_sinaplicar=0.00

        payment_cobro_amount = 0.00
        payment_cobro_interes = 0.00

        payment_cobro_amount_done = 0.00
        payment_cobro_interes_done = 0.00

        original_cobro_amount_sinaplicar = 0.00
        original_cobro_interes_sinaplicar = 0.00
        amount_retenido=0.00
        for line in self.line_ids:
            payment_capital+= round(line.payment_capital, DEC)
            payment_interest+= round(line.payment_interest, DEC)
            payment_other+= round(line.payment_other, DEC)

            original_payment_capital_sinaplicar += round(line.payment_capital, DEC)
            original_payment_interest_sinaplicar += round(line.payment_interest, DEC)
            original_payment_other_sinaplicar += round(line.payment_other, DEC)

            payment_cobro_amount += round(line.amount+line.amount_iva, DEC)
            payment_cobro_interes += round(line.amount_interes, DEC)

            original_cobro_amount_sinaplicar += round(line.amount+line.amount_iva, DEC)
            original_cobro_interes_sinaplicar += round(line.amount_interes, DEC)

            for brw_payment in line.payment_ids:
                if brw_payment.document_id.type!='contrato':
                    if not brw_payment.migrated:
                        if brw_payment.payment_id and brw_payment.payment_id.state == 'posted' and not brw_payment.payment_id.reversed_payment_id:
                            payment_capital_done+= round(brw_payment.payment_capital, DEC)
                            payment_interest_done+= round(brw_payment.payment_interest, DEC)
                            payment_other_done+= round(brw_payment.payment_other, DEC)
                    else:
                        if brw_payment.state == 'validated':
                            payment_capital_done += round(brw_payment.payment_capital, DEC)
                            payment_interest_done += round(brw_payment.payment_interest, DEC)
                            payment_other_done += round(brw_payment.payment_other, DEC)
                else:
                    if not brw_payment.migrated:
                        if brw_payment.payment_id and brw_payment.payment_id.state == 'posted' and not brw_payment.payment_id.reversed_payment_id:
                            payment_cobro_amount_done+= round(brw_payment.payment_amount, DEC)
                            payment_cobro_interes_done+= round(brw_payment.payment_interes_generado, DEC)
                    else:
                        if brw_payment.state == 'validated':
                            payment_cobro_amount_done += round(brw_payment.payment_amount, DEC)
                            payment_cobro_interes_done += round(brw_payment.payment_interes_generado, DEC)
            payment_cobro_amount_done += line.amount_retenido
        #############################################################################################
        self.payment_interest = round(payment_interest-payment_interest_done, DEC)
        self.payment_capital = round(payment_capital-payment_capital_done, DEC)
        self.payment_other=round(payment_other-payment_other_done,DEC)
        #############################################################################################
        self.original_payment_capital =self.payment_capital
        self.original_payment_interest = self.payment_interest
        self.original_payment_other = self.payment_other
        #############################################################################################
        original_payment_capital_sinaplicar=original_payment_capital_sinaplicar-payment_capital_done
        original_payment_interest_sinaplicar = original_payment_interest_sinaplicar - payment_interest_done
        original_payment_other_sinaplicar = original_payment_other_sinaplicar - payment_other_done
        self.original_payment_capital_sinaplicar = round(original_payment_capital_sinaplicar,DEC)
        self.original_payment_interest_sinaplicar =round( original_payment_interest_sinaplicar,DEC)
        self.original_payment_other_sinaplicar = round(original_payment_other_sinaplicar,DEC)


        #############################################################################################
        self.payment_cobro_amount=round(payment_cobro_amount-payment_cobro_amount_done,DEC)
        self.payment_cobro_interes = round(payment_cobro_interes-payment_cobro_interes_done,DEC)
        #############################################################################################
        self.original_cobro_amount = round(payment_cobro_amount-payment_cobro_amount_done,DEC)
        self.original_cobro_interes = round(payment_cobro_interes-payment_cobro_interes_done,DEC)
        self.original_cobro_amount_sinaplicar = round(original_cobro_amount_sinaplicar,DEC)
        self.original_cobro_interes_sinaplicar = round(original_cobro_interes_sinaplicar,DEC)

    @api.onchange('amount','years')
    def compute_capital(self):
        DEC=2
        for brw_each in self:
            capital=0.00
            periods=0
            percentage_amortize=0.00
            if brw_each.type == "compute":
                if brw_each.years>0:
                    periods=(brw_each.years*12)/3
                    capital=round(brw_each.amount/periods,DEC)
                    if periods>0:
                        percentage_amortize=round(100.00/float(periods),2)
            brw_each.capital=capital
            brw_each.periods=periods
            brw_each.percentage_amortize=percentage_amortize

    @api.constrains('amount')
    def validate_amount(self):
        for brw_each in self:
            if brw_each.type=="compute" and brw_each.type_action=="import":
                if brw_each.amount<=0.00:
                    raise ValidationError(_("El Valor Nominal debe ser mayor a 0"))

    @api.constrains('percentage_amortize')
    def validate_percentage_amortize(self):
        for brw_each in self:
            if brw_each.type == "compute" and brw_each.type_action=="import":
                if brw_each.percentage_amortize <= 0.00:
                    raise ValidationError(_("El % por Amortizar debe ser mayor a 0"))

    @api.constrains('percentage_interest')
    def validate_percentage_interest(self):
        for brw_each in self:
            if brw_each.type == "compute" and brw_each.type_action=="import":
                if brw_each.percentage_interest <= 0.00:
                    raise ValidationError(_("El % de Interes debe ser mayor a 0"))

    @api.constrains('percentage_interest_quota')
    def validate_percentage_interest_quota(self):
        for brw_each in self:
            if brw_each.type == "compute" and brw_each.type_action=="import":
                if brw_each.percentage_interest_quota <= 0.00:
                    raise ValidationError(_("El % de Interes de Cuota debe ser mayor a 0"))

    @api.constrains('years')
    def validate_years(self):
        for brw_each in self:
            if brw_each.type == "compute" and brw_each.type_action=="import":
                if brw_each.years <= 0.00:
                    raise ValidationError(_("El % de Interes debe ser mayor a 0"))

    def process(self):
        for brw_each in self:
            if brw_each.type!="file":
                brw_each.process_compute()
            else:#
                brw_each.process_file()
        return True

    def process_in(self):
        for brw_each in self:
            if brw_each.type!="file":
                raise ValidationError(_("Operacion no implementada"))
            else:#
                brw_each.process_file_in()
        return True

    def process_compute(self):
        DEC=2
        for brw_each in self:
            brw_each.validate_amount()
            brw_each.validate_percentage_amortize()
            brw_each.validate_percentage_interest()
            brw_each.validate_years()
            percentage_interest_quota=brw_each.percentage_interest_quota
            percentage_amortize=0.00
            if brw_each.periods:
                percentage_amortize = brw_each.percentage_amortize###acumular hacia arriba
            date_start=brw_each.document_financial_id.date_process
            date_maturity=date_start
            percentage_amortize_acum=0.00
            line_ids=[(5,)]
            for quota in range(1,brw_each.periods+1):
                date_process=date_start + relativedelta(months=quota*3)
                percentage_interest = (brw_each.percentage_interest - (percentage_interest_quota*(quota-1.00)))
                if quota == brw_each.periods:
                    percentage_amortize = 100.00 - percentage_amortize_acum
                else:
                     percentage_amortize_acum+=percentage_amortize

                date_maturity = date_start
                vals={
                    "quota":quota,
                    "date_process":date_process,
                    "percentage_amortize":percentage_amortize,
                    "percentage_interest":percentage_interest,
                    "payment_capital":round(brw_each.amount*percentage_amortize/100.00,DEC),
                    "payment_interest": round((brw_each.amount * percentage_interest/ 100.00), DEC),
                }
                line_ids.append((0,0,vals))
            brw_each.document_financial_id.write({"line_ids":line_ids,"date_maturity":date_maturity,
                                            "amount":brw_each.amount,
                                             "percentage_amortize": brw_each.percentage_amortize,
                                             "percentage_interest": brw_each.percentage_interest,
                                             "percentage_interest_quota": brw_each.percentage_interest_quota,
                                             "capital": brw_each.capital,
                                             "periods": brw_each.periods,
                                             "years": brw_each.years,
                                             "type_document":brw_each.type
                                             })
        return True

    def process_file_in(self):
        DEC=2
        DATE,QUOTA,TOTAL=0,1,2
        for brw_each in self:
            line_ids = [(5,)]
            ext = flObj.get_ext(brw_each.file_name)
            fileName = flObj.create(ext)
            flObj.write(fileName, flObj.decode64(brw_each.file))
            book = open_workbook(fileName)
            sheet = book.sheet_by_index(0)
            quota = 1
            date_maturity = brw_each.document_financial_id.date_process
            total_capital=0.00
            for row_index in range(1, sheet.nrows):
                quota= int(sheet.cell(row_index, QUOTA).value)
                amount = float(str(sheet.cell(row_index, TOTAL).value).replace(',', ''))
                str_date = str(sheet.cell(row_index, DATE).value)
                date_process = dtObj.parse(str_date, date_format="%d/%m/%Y")
                vals = {
                    "quota": quota,
                    "date_process": date_process,
                    'date_maturity_payment': date_process,
                    "amount": round(amount, DEC),
                    "amount_original": round(amount, DEC),
                }
                line_ids.append((0, 0, vals))
                date_maturity=date_process
                quota += 1
            periods = quota
            brw_each.document_financial_id.write({"line_ids": line_ids,
                                             "date_maturity": date_maturity,
                                             "amount": total_capital,
                                             "periods": periods,
                                             })
        return True

    def process_file2(self):
        DEC=2
        DATE,AMORTIZE_AMOUNT,AMOUNT_INTEREST,CAPITAL,INTEREST,TOTAL=0,1,2,3,4,5
        for brw_each in self:
            line_ids = [(5,)]
            ext = flObj.get_ext(brw_each.file_name)
            fileName = flObj.create(ext)
            flObj.write(fileName, flObj.decode64(brw_each.file))
            book = open_workbook(fileName)
            sheet = book.sheet_by_name("IMPORTAR")
            quota = 1
            date_maturity = brw_each.document_financial_id.date_process
            global_percentage_amortize=0.00
            total_capital=0.00
            for row_index in range(0, sheet.nrows):
                percentage_amortize= float(str(sheet.cell(row_index, AMORTIZE_AMOUNT).value))
                percentage_interest = float(str(sheet.cell(row_index, AMOUNT_INTEREST).value))
                capital = float(str(sheet.cell(row_index,CAPITAL ).value))
                total_capital+= capital
                interest = float(str(sheet.cell(row_index, INTEREST).value))
                str_date = str(sheet.cell(row_index, DATE).value)
                date_process = dtObj.parse(str_date,date_format="%d/%m/%Y")
                if row_index==0:
                    global_percentage_amortize=percentage_amortize
                vals = {
                    "quota": quota,
                    "date_process": date_process,
                    "percentage_amortize": percentage_amortize,
                    "percentage_interest": percentage_interest,
                    "payment_capital": round(capital, DEC),
                    "payment_interest": round(interest, DEC),
                }
                line_ids.append((0, 0, vals))
                date_maturity=date_process
                quota += 1
            periods = quota
            brw_each.document_financial_id.write({"line_ids": line_ids, "date_maturity": date_maturity,
                                             "amount": total_capital,
                                             "percentage_amortize": global_percentage_amortize,
                                             "percentage_interest": brw_each.percentage_interest,
                                             "percentage_interest_quota": brw_each.percentage_interest_quota,
                                             "capital": total_capital,
                                             "periods": periods,
                                             "years":periods/4,
                                             "type_document": brw_each.type
                                             })
        return True

    def process_file(self):
        DEC=2
        QUOTA ,  DATE_PROCESS ,   PAYMENT_CAPITAL, PAYMENT_INTEREST,    PAYMENT_OVERDUE_INTEREST ,   PAYMENT_OTHER ,  TOTAL=0,1,2,3,4,5,6
        for brw_each in self:
            line_ids = [(5,)]
            ext = flObj.get_ext(brw_each.file_name)
            fileName = flObj.create(ext)
            flObj.write(fileName, flObj.decode64(brw_each.file))
            book = open_workbook(fileName)
            sheet = book.sheet_by_index(0)
            quota = 1
            date_maturity = brw_each.document_financial_id.date_process
            global_percentage_amortize=0.00
            total_capital=0.00
            for row_index in range(1, sheet.nrows):
                quota = int(sheet.cell(row_index, QUOTA).value)
                payment_capital = float(str(sheet.cell(row_index, PAYMENT_CAPITAL).value).replace(',', ''))
                payment_interest = float(str(sheet.cell(row_index, PAYMENT_INTEREST).value).replace(',', ''))
                payment_overdue_interest= float(str(sheet.cell(row_index, PAYMENT_OVERDUE_INTEREST).value).replace(',', ''))
                payment_other = float(str(sheet.cell(row_index, PAYMENT_OTHER).value).replace(',', ''))
                #total = float(str(sheet.cell(row_index,TOTAL ).value))
                total_capital+= payment_capital
                str_date = str(sheet.cell(row_index, DATE_PROCESS).value)
                date_process = dtObj.parse(str_date,date_format="%d/%m/%Y")
                #if row_index==0:
                #    global_percentage_amortize=percentage_amortize
                vals = {
                    "quota": quota,
                    "date_process": date_process,
                    "payment_capital": round(payment_capital, DEC),
                    "payment_interest": round(payment_interest, DEC),
                    "payment_overdue_interest": round(payment_overdue_interest, DEC),
                    "payment_other": round(payment_other, DEC),
                }
                line_ids.append((0, 0, vals))
                date_maturity=date_process
                quota += 1
            periods = quota
            brw_each.document_financial_id.write({"line_ids": line_ids, "date_maturity": date_maturity,
                                             #"amount": total_capital,
                                             #"percentage_amortize": global_percentage_amortize,
                                             #"percentage_interest": brw_each.percentage_interest,
                                             #"percentage_interest_quota": brw_each.percentage_interest_quota,
                                             "capital": total_capital,
                                             "periods":abs(periods-1),
                                             "years": abs(periods-1)/4,
                                             "type_document": brw_each.type
                                             })
        return True

    def process_payment(self):
        for brw_each in self:
            brw_each._check_lines_valid_and_balanced()
            if brw_each.document_financial_id.internal_type=='out':
                brw_each.process_payment_supplier()
            if brw_each.document_financial_id.internal_type == 'in':
                brw_each.process_payment_customer()

    def process_payment_supplier(self):
        DEC = 2
        for brw_each in self:
            if not brw_each.line_ids:
                raise ValidationError(_("Debes definir al menos una linea"))
            if len(brw_each.line_ids)!=1:
                raise ValidationError(_("Debes definir solo una linea"))
            payment_amount = sum(line.total_pending for line in brw_each.line_ids)
            global_payment_amount=brw_each.payment_capital+brw_each.payment_interest+brw_each.payment_other+brw_each.payment_overdue_interest
            if round(brw_each.payment_overdue_interest, DEC) < 0.00:
                raise ValidationError(_("La cantidad ingresada por pagar Interes Mora debe ser mayor o igual a 0.00"))
            if round(global_payment_amount, DEC) > round(payment_amount, DEC):
                pass#raise ValidationError(_("La cantidad a pagar no puede ser mayor a lo pendiente") )
            if round(global_payment_amount, DEC) <= 0.00:
                raise ValidationError(_("La cantidad a pagar debe ser mayor a 0.00") )
            if round(payment_amount, DEC) < 0.00:
                raise ValidationError(_("La cantidad seleccionada a pagar debe ser mayor a 0.00")  )
            if payment_amount == 0:
                raise ValidationError(
                        "La cantidad pendiente total es cero, no es posible realizar la distribución.")
            remaining_amount = self.payment_total
            payment_capital=self.payment_capital
            payment_interest = self.payment_interest
            payment_overdue_interest = self.payment_overdue_interest
            payment_other = self.payment_other
            bank_line_payment_group_ids=self.env["document.financial.line.payment.group"]

            for line in brw_each.line_ids:
                if remaining_amount <= 0:
                    break  # Si ya no queda cantidad por aplicar, salimos

                # Determinamos cuánto podemos aplicar a la línea según su saldo pendiente
                amount_to_apply = min(line.total_pending, remaining_amount)

                # Reducimos la cantidad pendiente de la línea
                bank_line_payment_group_ids+=self.env["document.financial.line.payment.group"].create({
                    #
                    "document_id": line.document_id.id,
                    "company_id": line.document_id.company_id.id,
                    "date_process":brw_each.payment_date,
                    #"amount":amount_to_apply,
                    #"payment_capital": payment_capital,
                    #"payment_interest": payment_interest,
                    #"payment_overdue_interest": payment_overdue_interest,
                    #"payment_other": payment_other,
                    "ref":brw_each.ref,
                    "name":brw_each.name,
                    "migrated":not brw_each.do_account,
                    "internal_type":line.document_id.internal_type,
                    "payment_line_ids":[(5,),
                         (0,0,{
                             "line_id": line.id,
                             "amount": amount_to_apply,
                             "payment_capital": payment_capital,
                             "payment_interest": payment_interest,
                             "payment_overdue_interest": payment_overdue_interest,
                             "payment_other": payment_other,
                         })]
                })

                # Restamos lo aplicado de la cantidad total a distribuir
                remaining_amount -= amount_to_apply

            # Si después de distribuir no se ha cubierto toda la cantidad, mostramos un error
            if round(remaining_amount,DEC) < 0:
                raise ValidationError(f"No se pudo aplicar el monto completo. Quedan {remaining_amount}.")
            ######################################crear pagos#########################################
            if brw_each.do_account:
                brw_each.create_acct_payment_supplier(bank_line_payment_group_ids)
            attachment_ids=[(4,attc.id) for attc in brw_each.attachment_ids]
            brw_each.line_ids.write({"attachment_ids":attachment_ids})
            ##########################################################################################
        return True

    def create_acct_payment_supplier(self,bank_line_payment_group_ids):
        payment_obj=self.env["account.payment"]
        self.ensure_one()
        brw_each =self
        OBJ_PERIOD_LINE = self.env["account.fiscal.year.line"].sudo()
        payment_date = fields.Date.context_today(self)
        brw_period, brw_period_line = OBJ_PERIOD_LINE.get_periods(payment_date, brw_each.company_id,
                                                                  for_account_payment=True)
        ref=brw_each.ref
        account_payment_method_manual_out = self.env.ref('account.account_payment_method_manual_out')
        outbound_payment_account_line = brw_each.journal_id.outbound_payment_method_line_ids.filtered(
            lambda line: line.payment_method_id == account_payment_method_manual_out
        )
        bank_account_id = outbound_payment_account_line.payment_account_id and outbound_payment_account_line.payment_account_id.id or self.journal_id.default_account_id.id
        payment_res = {
            'payment_type': "outbound",
            'partner_id':brw_each.document_financial_id.partner_id and brw_each.document_financial_id.partner_id.id or False,
            'partner_type': "supplier",
            'journal_id': brw_each.journal_id.id,
            'company_id':  brw_each.company_id.id,
            'currency_id':  brw_each.company_id.currency_id.id,
            'date':brw_each.payment_date,
            'payment_method_id': account_payment_method_manual_out.id,
            'ref': ref,
            'is_prepayment':False,
            'period_id': brw_period.id,
            'period_line_id': brw_period_line.id,
            'payment_purchase_line_ids': [(5,)],
            "destination_account_id":bank_account_id,
            'change_payment':True,
            "document_financial_id":brw_each.document_financial_id.id,
            "document_financial_payment_group_id":bank_line_payment_group_ids and bank_line_payment_group_ids.id or False
        }
        payment_line_ids = []
        amount= 0.00
        for brw_line_account in brw_each.line_account_ids:
            if bank_account_id!= brw_line_account.account_id.id:
                payment_line_ids.append((0, 0, {
                        "account_id": brw_line_account.account_id.id,
                        "partner_id": brw_line_account.partner_id and brw_line_account.partner_id.id or False,
                        "name": ref,
                        "credit":brw_line_account.credit,
                        "debit": brw_line_account.debit,
                        "analytic_id":brw_line_account.analytic_id and brw_line_account.analytic_id.id or False
                }))
            else:
                amount += brw_line_account.credit
        payment_res["amount"] = amount
        payment_res["payment_line_ids"] = payment_line_ids
        payment = payment_obj.create(payment_res)
        payment.action_post()
        bank_line_payment_group_ids.payment_line_ids.write({"payment_id":payment.id})

    ###########################################

    def process_payment_customer(self):
        DEC = 2
        for brw_each in self:
            if not brw_each.line_ids:
                raise ValidationError(_("Debes definir al menos una linea"))
            payment_amount = sum(line.total_pending for line in brw_each.line_ids)
            global_payment_amount = brw_each.payment_total#+brw_each.payment_overdue_interest
            # if round(global_payment_amount, DEC) > round(payment_amount, DEC):
            #     raise ValidationError(_("La cantidad a cobrar no puede ser mayor a lo pendiente") )
            if round(global_payment_amount, DEC) <= 0.00:
                raise ValidationError(_("La cantidad a cobrar debe ser mayor a 0.00"))
            if round(payment_amount, DEC) < 0.00:
                raise ValidationError(_("La cantidad seleccionada a cobrar debe ser mayor a 0.00"))
            if payment_amount == 0:
                raise ValidationError(
                        "La cantidad pendiente total es cero, no es posible realizar la distribución.")
            # if brw_each.payment_overdue_interest>0:
            #     if len(brw_each.line_ids)>1:
            #         raise ValidationError(_("No puedes asignar un interes por mas de una linea"))
            remaining_amount = brw_each.payment_total

            payment_cobro_amount = brw_each.payment_cobro_amount
            payment_cobro_interes = brw_each.payment_cobro_interes

            payment_line_ids= [(5,),]

            if brw_each.payment_total>0:
                for line in brw_each.line_ids:
                    if remaining_amount <= 0:
                        break  # Si ya no queda cantidad por aplicar, salimos

                    # Determinamos cuánto podemos aplicar a la línea según su saldo pendiente
                    amount_to_apply = min(line.total_pending, remaining_amount)

                    # Reducimos la cantidad pendiente de la línea

                    payment_line_ids+=[(0, 0, {
                        "line_id": line.id,
                        "payment_amount": payment_cobro_amount,
                        "payment_interes_generado": payment_cobro_interes,

                        "amount": payment_cobro_amount+ payment_cobro_interes,

                    })]
                    # Restamos lo aplicado de la cantidad total a distribuir
                    remaining_amount -= amount_to_apply


            bank_line_payment_group_ids = self.env["document.financial.line.payment.group"].create({
                #
                "document_id": brw_each.document_financial_id.id,
                "company_id":brw_each.document_financial_id.company_id.id,
                "date_process": brw_each.payment_date,
                "ref": brw_each.ref,
                "name": brw_each.name,
                "internal_type": brw_each.document_financial_id.internal_type,
                "payment_line_ids": payment_line_ids,
                "migrated": not brw_each.do_account,
            })

            # Si después de distribuir no se ha cubierto toda la cantidad, mostramos un error
            if round(remaining_amount,DEC) < 0:
                raise ValidationError(f"Could not apply the full amount. {remaining_amount} remains.")
            ######################################crear pagos#########################################
            if brw_each.do_account:
                brw_each.create_acct_payment_customer(bank_line_payment_group_ids)
            attachment_ids=[(4,attc.id) for attc in brw_each.attachment_ids]
            brw_each.line_ids.write({"attachment_ids":attachment_ids})
            ##########################################################################################
        return True

    def create_acct_payment_customer(self,bank_line_payment_group_ids):
        payment_obj=self.env["account.payment"]
        self.ensure_one()
        brw_each =self
        OBJ_PERIOD_LINE = self.env["account.fiscal.year.line"].sudo()
        payment_date = fields.Date.context_today(self)
        brw_period, brw_period_line = OBJ_PERIOD_LINE.get_periods(payment_date, brw_each.company_id,
                                                                  for_account_payment=True)
        ref=brw_each.ref
        account_payment_method_manual_in = self.env.ref('account.account_payment_method_manual_in')
        inbound_payment_account_line = brw_each.journal_id.inbound_payment_method_line_ids.filtered(
            lambda line: line.payment_method_id == account_payment_method_manual_in
        )
        #print(account_payment_method_manual_in)
        bank_account_id = inbound_payment_account_line.payment_account_id and inbound_payment_account_line.payment_account_id.id or self.journal_id.default_account_id.id
        #print(bank_line_payment_ids.line_id)
        payment_res = {
            'payment_type': "inbound",
            'partner_id':brw_each.document_financial_id.partner_id and brw_each.document_financial_id.partner_id.id or False,
            'partner_type': "customer",
            'journal_id': brw_each.journal_id.id,
            'company_id':  brw_each.company_id.id,
            'currency_id':  brw_each.company_id.currency_id.id,
            'date':brw_each.payment_date,
            'payment_method_id': account_payment_method_manual_in.id,
            'ref': ref,
            'is_prepayment':False,
            'period_id': brw_period.id,
            'period_line_id': brw_period_line.id,
            'payment_purchase_line_ids': [(5,)],
            "destination_account_id":bank_account_id,
            'change_payment':True,
            "document_financial_id":brw_each.document_financial_id.id,
            "document_financial_payment_group_id":bank_line_payment_group_ids and bank_line_payment_group_ids.id or False
        }
        payment_line_ids = []
        amount=0.00
        for brw_line_account in brw_each.line_account_ids:
            if bank_account_id!= brw_line_account.account_id.id:
                payment_line_ids.append((0, 0, {
                        "account_id": brw_line_account.account_id.id,
                        "partner_id": brw_line_account.partner_id and brw_line_account.partner_id.id or False,
                        "name": ref,
                        "credit":brw_line_account.credit,
                        "debit": brw_line_account.debit,
                     "analytic_id":brw_line_account.analytic_id and brw_line_account.analytic_id.id or False
                }))
            else:
                amount+=brw_line_account.debit
        payment_res["payment_line_ids"] = payment_line_ids
        payment_res["amount"]=amount
        payment = payment_obj.create(payment_res)
        payment.action_post()
        bank_line_payment_group_ids.payment_line_ids.write({"payment_id":payment.id})

    def process_invoice(self):
        DEC = 2
        for brw_each in self:
            if not brw_each.invoice_ids:
                raise ValidationError(_("Debes definir al menos una factura"))
            for brw_line in brw_each.financial_line_ids:
                brw_line.write({"invoice_ids": [(5,)]})
            invoices = brw_each.invoice_ids #+ old_invoices
            if not brw_each.financial_line_ids:
                raise ValidationError(_("Debes seleccionar al menos una cuota"))
            if not invoices:
                raise ValidationError(_("Debes seleccionar al menos una factura"))

            for brw_line_invoiced in brw_each.invoiced_line_ids:
                if brw_line_invoiced.invoice_id:
                    invoice_ids = []
                    invoice_ids.append((0,0,{
                                 "line_id": brw_line_invoiced.line_id.id,
                                 "company_id": brw_line.document_id.company_id.id,
                                 "amount_retenido":round(brw_line_invoiced.amount_retenido,DEC),
                                 "amount_base":round( brw_line_invoiced.amount_base,DEC),
                                 "amount":  round(brw_line_invoiced.amount,DEC),
                                 "amount_iva": round(brw_line_invoiced.amount_iva,DEC),
                                 "invoice_id": brw_line_invoiced.invoice_id.id,
                    }))
                    brw_line_invoiced.line_id.invoice_ids=invoice_ids
            return True

    ###########################################

    def process_payment_cobro(self):
        DEC = 2
        for brw_each in self:
            brw_each._check_lines_valid_and_balanced()
            if round(brw_each.payment_collect, DEC) > round(brw_each.payment_amount_collect, DEC):
                raise ValidationError(_("La cantidad a recaudar no puede ser mayor a lo pendiente") )
            if round(brw_each.payment_collect, DEC) <= 0.00:
                raise ValidationError(_("La cantidad a recaudar debe ser mayor a 0.00"))

            bank_line_payment_group_ids = self.env["document.financial.line.payment.group"].create({
                #
                "document_cobro_id": brw_each.document_financial_id.id,
                "company_id":brw_each.document_financial_id.company_id.id,
                "date_process": brw_each.payment_date,
                "ref": brw_each.ref,
                "name": brw_each.name,
                "internal_type":'in',
                "migrated": not brw_each.do_account,
                "payment_line_ids":[(5,),
                                    (0, 0, {  "amount": brw_each.payment_collect,  })]
            })
            if brw_each.do_account:
                brw_each.create_acct_payment_cobro(bank_line_payment_group_ids)
            ##########################################################################################
            attachment_ids = [(4, attc.id) for attc in brw_each.attachment_ids]
            brw_each.write({"attachment_ids": attachment_ids})
        return True

    def create_acct_payment_cobro(self,bank_line_payment_group_ids):
        payment_obj = self.env["account.payment"]
        self.ensure_one()
        brw_each = self
        OBJ_PERIOD_LINE = self.env["account.fiscal.year.line"].sudo()
        payment_date = fields.Date.context_today(self)
        brw_period, brw_period_line = OBJ_PERIOD_LINE.get_periods(payment_date, brw_each.company_id,
                                                                  for_account_payment=True)
        ref = brw_each.ref
        account_payment_method_manual_in = self.env.ref('account.account_payment_method_manual_in')
        inbound_payment_account_line = brw_each.journal_id.inbound_payment_method_line_ids.filtered(
            lambda line: line.payment_method_id == account_payment_method_manual_in
        )
        # print(account_payment_method_manual_in)
        bank_account_id = inbound_payment_account_line.payment_account_id and inbound_payment_account_line.payment_account_id.id or self.journal_id.default_account_id.id
        # print(bank_line_payment_ids.line_id)
        payment_res = {
            'payment_type': "inbound",
            'partner_id': brw_each.document_financial_id.partner_id and brw_each.document_financial_id.partner_id.id or False,
            'partner_type': "customer",
            'journal_id': brw_each.journal_id.id,
            'company_id': brw_each.company_id.id,
            'currency_id': brw_each.company_id.currency_id.id,
            'date': brw_each.payment_date,

            'payment_method_id': account_payment_method_manual_in.id,
            'ref': ref,
            'is_prepayment': False,
            'period_id': brw_period.id,
            'period_line_id': brw_period_line.id,
            'payment_purchase_line_ids': [(5,)],
            "destination_account_id": bank_account_id,
            'change_payment': True,
            "document_financial_id": brw_each.document_financial_id.id,
            "document_financial_payment_group_id": bank_line_payment_group_ids and bank_line_payment_group_ids.id or False
        }
        payment_line_ids = []
        payment_collect=0.00
        for brw_line_account in brw_each.line_account_ids:
            if bank_account_id != brw_line_account.account_id.id:
                payment_line_ids.append((0, 0, {
                    "account_id": brw_line_account.account_id.id,
                    "partner_id": brw_line_account.partner_id and brw_line_account.partner_id.id or False,
                    "name": ref,
                    "credit": brw_line_account.credit,
                    "debit": brw_line_account.debit,
                    "analytic_id":brw_line_account.analytic_id and brw_line_account.analytic_id.id or False
                }))
            else:
                payment_collect = brw_line_account.debit#+brw_line_account.credit
        payment_res['amount']= payment_collect

        payment_res["payment_line_ids"] = payment_line_ids
        payment = payment_obj.create(payment_res)
        payment.action_post()
        bank_line_payment_group_ids.payment_line_ids.write({"payment_id": payment.id})

    def _check_lines_valid_and_balanced(self):
        for wizard in self:
            total_debit = 0.0
            total_credit = 0.0

            if not wizard.line_account_ids:
                raise ValidationError("Debe agregar al menos una línea de operación financiera.")

            for line in wizard.line_account_ids:
                if not line.account_id:
                    raise ValidationError("Todas las líneas deben tener una cuenta contable.")
                #if not line.partner_id:
                #    raise ValidationError("Todas las líneas deben tener un contacto asignado.")
                if line.debit <= 0.0 and line.credit <= 0.0:
                    raise ValidationError("Cada línea debe tener un valor mayor a 0.00 en 'Debe' o 'Haber'.")
                total_debit += line.debit
                total_credit += line.credit

            # Redondeo para evitar errores por decimales flotantes
            if round(total_debit, 2) != round(total_credit, 2):
                raise ValidationError("El asiento no está balanceado: el total del Debe y el Haber deben coincidir.")

    @api.onchange('financial_line_ids', 'invoice_ids')
    def _onchange_financial_or_invoiced(self):
        """Generar detalle en invoiced_line_ids al cambiar las cuotas,
        distribuyendo facturas sin superar el total_to_invoice total
        y agregando una línea con saldo pendiente sin factura.
        """
        lines_vals = [(5,)]  # Limpia las líneas previas
        DEC = 2

        if not self.financial_line_ids:
            self.invoiced_line_ids = []
            return

        # Total global disponible a facturar
        restante = round(sum(self.financial_line_ids.mapped('total_to_invoice')), DEC)

        # Total de retenciones de todas las facturas

        # Asignar facturas a las líneas (puede haber varias facturas y varias cuotas)
        if self.invoice_ids:
            for financial_line in self.financial_line_ids:
                for inv in self.invoice_ids:
                    if restante <= 0:
                        break

                    withholds = sum(
                        inv.get_withholds().mapped('amount_total_signed')) if inv else 0.0


                    monto_factura = round(inv.amount_total, DEC)
                    monto_asignado = min(monto_factura, restante)
                    monto_base = round(inv.amount_untaxed, DEC)
                    monto_iva = round(inv.amount_total - inv.amount_untaxed, DEC)

                    lines_vals.append((0, 0, {
                        'line_id': financial_line.id,
                        'invoice_id': inv.id,
                        'amount': monto_asignado,
                        'amount_base': round(monto_base, DEC),
                        'amount_iva':round(monto_iva, DEC),
                        'amount_retenido': round(withholds, DEC),
                    }))

                    restante -= monto_asignado

        # Si queda saldo pendiente sin factura, agregamos una línea
        if restante > 0:
            lines_vals.append((0, 0, {
                'line_id': False,
                'invoice_id': False,
                'amount': restante,
                'amount_base': restante,
                'amount_iva': 0.0,
                'amount_retenido': 0.0,
            }))

        self.invoiced_line_ids = lines_vals

class DocumentFinancialLineWizard(models.Model):
    _name = "document.financial.line.wizard"
    _description = "Detalle de Asistente de Operacion Financiera"

    wizard_id=fields.Many2one('document.financial.wizard','Asistente',ondelete="cascade")
    company_id=fields.Many2one(related="wizard_id.company_id",store=False,readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)
    account_id = fields.Many2one('account.account', 'Cuenta', required=True)
    partner_id = fields.Many2one('res.partner', 'Contacto', required=False)
    debit=fields.Monetary("Debe",required=True)
    credit = fields.Monetary("Haber", required=True)
    is_prepayment = fields.Boolean("Es Anticipo", default=False,compute="_compute_is_prepayment")
    analytic_id = fields.Many2one("account.analytic.account", "Cuenta Analitica")

    @api.onchange('account_id')
    @api.depends('account_id')
    def _compute_is_prepayment(self):
        for brw_each in self:
            account = brw_each.account_id
            is_prepayment = False
            if account and account.account_type == 'asset_prepayments' \
                    and not account.deprecated \
                    and account.prepayment_account:
                is_prepayment = True
            brw_each.is_prepayment = is_prepayment

class DocumentFinancialLineInvoicedWizard(models.Model):
    _name = "document.financial.line.invoiced.wizard"
    _description = "Detalle de Asistente de Facturas para Operaciones Financieras"

    wizard_id=fields.Many2one('document.financial.wizard','Asistente',ondelete="cascade")
    company_id=fields.Many2one(related="wizard_id.company_id",store=False,readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)
    line_id=fields.Many2one('document.financial.line','Cuota')
    invoice_id = fields.Many2one('account.move', 'Factura')
    amount = fields.Monetary("Aplicado", default=0.00, required=True)
    amount_base = fields.Monetary("Valor Base", default=0.00, required=True)
    amount_iva = fields.Monetary("Valor IVA", default=0.00, required=True)
    amount_retenido = fields.Monetary("Valor Retenido", default=0.00, required=True)





class DocumentBankWizard(models.Model):
    _name = "document.bank.wizard"

class DocumentBankLineWizard(models.Model):
    _name = "document.bank.line.wizard"