    # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import re
import re
from ..models import DEFAULT_MODE_PAYMENTS

class AccountPaymentRequestWizard(models.Model):
    _name = 'account.payment.request.wizard'
    _description = "Asistente de Solicitud de Pagos"

    @api.model
    def _get_default_request_id(self):
        return self._context.get("active_ids") and self._context.get("active_ids")[0] or False

    def extraer_doc_y_numero(self,texto):
        match = re.search(r'^(.*?)\s+\d{3}-\d{3}-(\d+)$', texto)
        if match:
            nombre = match.group(1)  # Todo antes del primer bloque de números
            numero = int(match.group(2))  # Últimos dígitos sin ceros a la izquierda
            return f"{nombre} {numero}"
        return texto  # Devuelve el original si no coincide

    @api.model
    def _get_default_payment_request_ids(self):
        def get_account_id(brw_request):
            if not brw_request.type in ('purchase.order','request') or brw_request.enable_other_account:
                return False
            brw_conf = self.env["account.configuration.payment"].sudo().search([('company_id', '=', brw_request.company_id.id)])
            if brw_request.partner_id.country_id==brw_request.company_id.country_id:##ecuador
                return brw_conf.local_prepayment_account_id and brw_conf.local_prepayment_account_id.id or False
            return brw_conf.exterior_prepayment_account_id and brw_conf.exterior_prepayment_account_id.id or False
        def get_bank_account_ids(brw_request):
            if brw_request.default_mode_payment!='bank':
                return False
            if brw_request.type=='hr.employee.payment':
                if brw_request.payment_employee_id:
                    if brw_request.payment_employee_id.movement_line_ids:
                        bank_ids=brw_request.payment_employee_id.movement_line_ids[0].employee_id.bank_account_id
                        return bank_ids.id
                    if brw_request.payment_employee_id.payslip_line_ids:
                        bank_ids=brw_request.payment_employee_id.payslip_line_ids[0].employee_id.bank_account_id
                        return bank_ids.id
                    return False
            return brw_request.partner_id.bank_ids and brw_request.partner_id.bank_ids[0].id or False
        active_ids= self._context.get("active_ids",[])
        lines=[(5,)]
        for brw_request in self.env["account.payment.request"].browse(active_ids):
            comments = brw_request.name#manual
            if brw_request.type == 'purchase.order':
                comments = 'ANT SERV %s' % brw_request.order_id.name+(brw_request.percentage>0.00 and " - "+str(brw_request.percentage)+" % " or "")
            elif brw_request.type == 'account.move':
                comments = self.extraer_doc_y_numero(brw_request.invoice_id.name)
                if brw_request.invoice_id.move_type=='in_invoice':
                    if brw_request.invoice_id.l10n_latam_document_type_id.code=='03':
                        comments=(brw_request.invoice_id.ref and "PAGO "+brw_request.invoice_id.ref+" -")+comments
            lines.append((0,0,{
                "counter":len(brw_request.partner_id.bank_ids),
                "request_id":brw_request.id,
                "pending": brw_request.pending,
                "amount": not brw_request.invoice_line_id  and brw_request.pending or min(brw_request.pending,abs(brw_request.invoice_line_id.amount_residual)) ,
                'bank_account_id':get_bank_account_ids(brw_request),
                "is_prepayment": (brw_request.type in ('purchase.order','request')) and not brw_request.enable_other_account,
                'comments':comments and comments.upper() or None,
                'prepayment_account_id':get_account_id(brw_request),
                'lock_account':brw_request.enable_other_account,
                "default_mode_payment":brw_request.default_mode_payment
             }))
        print(lines)
        return lines

    @api.model
    def _get_default_payment_requests(self):
        active_ids = self._context.get("active_ids", [])
        amount=0.00
        for brw_request in self.env["account.payment.request"].browse(active_ids):
            amount+=brw_request.pending
        return amount

    @api.model
    def _get_default_code(self):
        return self.env["ir.sequence"].sudo().next_by_code("bank.macro.request")

    @api.model
    def _get_default_date_request(self):
        return fields.Date.context_today(self)

    @api.model
    def _get_default_mode_payment(self):
        active_ids = self._context.get("active_ids", [])
        for brw_request in self.env["account.payment.request"].browse(active_ids):
            default_mode_payment = brw_request.default_mode_payment
            return default_mode_payment
        return None

    code=fields.Char("# Proceso",default=_get_default_code)
    request_id = fields.Many2one("account.payment.request", "Solicitud", ondelete="cascade", default=_get_default_request_id)
    company_id = fields.Many2one(related="request_id.company_id", store=False, readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)

    journal_id=fields.Many2one("account.journal","Diario",required=True)
    amount=fields.Monetary(string="Pagado",compute="_compute_total",store=False,readonly=True)
    pending = fields.Monetary(string="Pendiente",compute="_compute_total",store=False,readonly=True)
    payment_request_ids = fields.One2many("account.payment.request.line.wizard","wizard_id","Solicitudes",default=_get_default_payment_request_ids)
    max_amount_payments=fields.Monetary("Monto Límite",required=True,default=_get_default_payment_requests)
    dif_max_amount_payments=fields.Monetary(string="Diferencias",compute="_compute_total",store=False,readonly=True)
    comments=fields.Text("Comentarios",required=True)
    date_request=fields.Date("Fecha de Solicitud",required=True,default=_get_default_date_request)

    generate_macro = fields.Boolean("Generar Macro", default=False)
    conf_payment_id = fields.Many2one('account.configuration.payment', 'Configuracion de Pago', required=True)
    enable_journal_ids=fields.Many2many(related="conf_payment_id.journal_ids",store=False,readonly=True)
    enable_bank_journal_ids=fields.Many2many("account.journal","acct_payment_request_bank_journal_rel","wizard_id","journal_id","Diarios de Bancos")

    default_mode_payment = fields.Selection(DEFAULT_MODE_PAYMENTS, string="Forma de Pago",default=_get_default_mode_payment)

    tipo_partner_pago = fields.Selection(
        selection=[('local', 'Local'), ('exterior', 'Exterior')],
        string="Tipo de Pago a Proveedor", default="local", required=True
    )

    @api.onchange('company_id', 'tipo_partner_pago', 'default_mode_payment')
    def onchange_company_id(self):
        self.enable_journal_ids = [(6, 0, [])]
        self.enable_bank_journal_ids = [(6, 0, [])]
        self.conf_payment_id = False

        if not self.company_id:
            return

        # Buscar configuración por compañía
        conf_payment = self.env["account.configuration.payment"].sudo().search([
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if conf_payment:
            self.conf_payment_id = conf_payment.id

            # Todos los diarios configurados
            journals = conf_payment.journal_ids

            # Aplicar filtro por tipo de proveedor
            if self.tipo_partner_pago == 'local':
                journals = journals.filtered(lambda j: j.for_local_payment)
            elif self.tipo_partner_pago == 'exterior':
                journals = journals.filtered(lambda j: j.for_exterior_payment)

            # Aplicar filtro por forma de pago
            if self.default_mode_payment == 'check':
                journals = journals.filtered(lambda j: j.for_check)
            elif self.default_mode_payment == 'bank':
                journals = journals.filtered(lambda j: j.for_bank)
            elif self.default_mode_payment == 'credit_card':
                journals = journals.filtered(lambda j: j.for_tc)

            # Asignar diarios habilitados
            self.enable_journal_ids = [(6, 0, journals.ids)]
            self.enable_bank_journal_ids = [(6, 0, conf_payment.mapped('bank_conf_ids.journal_ids').ids)]

    @api.onchange('company_id','journal_id','conf_payment_id','enable_journal_ids','enable_bank_journal_ids')
    def onchange_journal_id(self):
        generate_macro=False
        if self.journal_id and self.enable_bank_journal_ids:
            generate_macro=(self.journal_id.id in self.enable_bank_journal_ids.ids)
        self.generate_macro=generate_macro

    @api.onchange('max_amount_payments')
    def _onchange_max_amount_payments(self):
        if self.max_amount_payments <= 0:
            raise ValidationError("El monto límite debe ser mayor a 0.")

    @api.depends('max_amount_payments','payment_request_ids', 'payment_request_ids.pending', 'payment_request_ids.amount')
    def _compute_total(self):
        for brw_each in self:
            brw_each.onchange_amounts()

    @api.onchange('max_amount_payments', 'payment_request_ids', 'payment_request_ids.pending',
                  'payment_request_ids.amount')
    def onchange_amounts(self):
        DEC = 2
        brw_each=self
        amount, pending, dif_max_amount_payments = 0.00, 0.00, 0.00
        for brw_line in brw_each.payment_request_ids:
            amount += brw_line.amount
            pending += brw_line.pending
        brw_each.amount = round(amount, DEC)
        brw_each.pending = round(pending, DEC)
        brw_each.dif_max_amount_payments = round(brw_each.max_amount_payments - amount, DEC)

    def check_unique_payment_account_per_partner(self):
        """
        Verifica que no existan múltiples cuentas contables diferentes para el mismo partner_id
        si el tipo de solicitud es 'account.move'
        """
        for wizard in self:
            partner_account_map = {}

            for line in wizard.payment_request_ids:
                if line.type == 'account.move':
                    partner_key = line.partner_id.id
                    account_id = line.payment_account_id.id

                    if partner_key in partner_account_map:
                        if partner_account_map[partner_key] != account_id:
                            raise ValidationError(
                                f"El proveedor '{line.partner_id.name}' tiene más de una cuenta contable de pago en el asistente."
                            )
                    else:
                        partner_account_map[partner_key] = account_id

    def process(self):
        DEC=2
        self.ensure_one()
        self._onchange_max_amount_payments()
        #self.check_unique_payment_account_per_partner()
        brw_each=self
        payment_obj=self.env["account.payment.bank.macro"]
        dscr_payments="Pagos a Proveedores"
        payment_res = {
            'company_id': brw_each.company_id.id,
            'journal_id': brw_each.journal_id.id,
            "generate_macro":brw_each.generate_macro,
            'conf_payment_id':brw_each.conf_payment_id.id,
            'name': brw_each.code,
            'date_request': brw_each.date_request,
            'date_payment': None,
            'state': 'draft',
            'comments': brw_each.comments,
            "max_amount_payments": brw_each.max_amount_payments,
            "mode_macro":"group",
            "type_module": "financial",
            'default_mode_payment':brw_each.default_mode_payment,
            "tipo_partner_pago":brw_each.tipo_partner_pago,
        }
        line_ids=[(5,)]
        if round(self.dif_max_amount_payments,DEC)<0.00:
            raise ValidationError(_("No puedes realizar un pago que supere el límite establecido de %s") % (self.max_amount_payments,))
        if not self.payment_request_ids:
            raise ValidationError(_("Al menos una solicitud debe ser definida"))
        ########################################################################
        types = set(brw_line.request_id.type for brw_line in self.payment_request_ids if brw_line.request_id)
        if 'hr.employee.payment' in types and (
                'account.move' in types or 'purchase.order' in types
        ):
            raise ValidationError(
                "No se permite procesar solicitudes que mezclen pagos a empleados con facturas u órdenes de compra."
            )
        for brw_line in self.payment_request_ids:
            if not brw_each.request_id.checked:
                raise ValidationError(_("La Solicitud %s no puede ser pagada al no estar verificada") % (brw_each.request_id.name,))
            if brw_line.amount>brw_line.pending:
                raise ValidationError(_("No puedes pagar mas de lo solicitado %s,%s") % (brw_line.request_id.id,brw_line.request_id.name))
            if brw_line.request_id.state!='confirmed':
                raise ValidationError(_("La Solicitud %s,%s debe estar en estado confirmado") % (brw_line.request_id.id,brw_line.request_id.name))
            ############################################
            if brw_line.request_id.type == 'account.move':
                lines=brw_line.request_id.invoice_line_ids
                invoices=".".join(lines.mapped('move_id.name'))
                total = abs(sum(lines.mapped('amount_residual')))
                if brw_line.amount > total:
                    raise ValidationError(
                        _("El valor de la solicitud de las Facturas %s NO debe ser mayor al valor pendiente %s de %s ") % (invoices,brw_line.amount,total))
            if brw_line.request_id.type == 'purchase.order':
                if brw_line.amount > brw_line.request_id.order_id.total_dif_payments_advances:
                    raise ValidationError(
                        _("El valor de la solicitud de la OC %s NO debe ser mayor al valor pendiente %s de %s") % (brw_line.request_id.order_id.name,brw_line.amount,brw_line.request_id.order_id.total_dif_payments_advances) )
            if brw_line.request_id.type=='hr.employee.payment':
                dscr_payments='Pagos de Nómina'
                payment_res['type_module']='payslip'
            if brw_line.request_id.type=='hr.employee.liquidation':
                dscr_payments='Liquidación de Haberes'
                payment_res['type_module']='payslip'
            if brw_line.request_id.type == 'request':
                if brw_line.request_id.enable_other_account and len(brw_line.request_id.payment_line_ids)>1:
                    if round(brw_line.amount, DEC) != round(brw_line.request_id.amount, DEC):
                        raise ValidationError(_("Los pagos parciales no están permitidos para solicitudes con cuentas de contrapartida. Ingrese el valor total a aplicar"))
            ###########################################
            if brw_each.default_mode_payment=='bank':
                if not brw_line.bank_account_id:
                    raise ValidationError(_("Todos los pagos deben tener definidos una cuenta bancaria destino.Revisa %s") % (brw_line.request_id.name,))
                ###########################################
                acc_number=brw_line.bank_account_id.acc_number
                if not re.fullmatch(r'[0-9]+', acc_number) or re.fullmatch(r'0+', acc_number):
                    raise ValidationError(
                        _("La cuenta bancaria asociada en %s debe contener solo números y no ser todo ceros.") % (
                        brw_line.request_id.name,))

            ###########################################
            if brw_line.is_prepayment and not brw_line.prepayment_account_id:
                raise ValidationError(_("Si es anticipo debes seleccionar una cuenta para anticipo"))
            line_ids.append((0,0,{
                "request_id":brw_line.request_id.id,
                "pending":brw_line.pending,
                "amount": brw_line.amount,
                "original_pending": brw_line.pending,
                "original_amount": brw_line.amount,
                'bank_account_id':brw_line.bank_account_id.id,
                'is_prepayment':brw_line.is_prepayment,
                "prepayment_account_id": brw_line.prepayment_account_id and brw_line.prepayment_account_id.id or False,
                'comments':brw_line.comments
            }))
        payment_res["line_ids"]=line_ids
        payment = payment_obj.create(payment_res)
        payment.onchange_mode_macro()
        payment.action_generated()
        OBJ_MODEL_DATA = self.env["ir.model.data"].sudo()
        form_id = OBJ_MODEL_DATA.resolve_view_ref("gps_bancos", "account_payment_bank_macro_view_form")
        tree_id = OBJ_MODEL_DATA.resolve_view_ref("gps_bancos", "account_payment_bank_macro_view_tree")
        calendar_id = OBJ_MODEL_DATA.resolve_view_ref("gps_bancos", "account_payment_bank_macro_view_calendar")
        context={}
        v = {
            'name': dscr_payments,
            'view_mode': 'form',
            'res_model': "account.payment.bank.macro",
            'views': [(form_id, 'form'),
                      (tree_id, 'tree'),
                      (calendar_id, 'calendar')],
            "context": context,
            "res_id":payment.id,
            'domain':f"[('id','=',{payment.id})]",
            'type': 'ir.actions.act_window'
        }
        return v

class AccountPaymentRequestPurchaseLineWizard(models.Model):
    _name = 'account.payment.request.line.wizard'
    _description = "Detalle de Asistente de Solicitud de Pagos"

    default_mode_payment = fields.Selection(DEFAULT_MODE_PAYMENTS, string="Forma de Pago", default="bank")

    counter=fields.Integer("# C.",help="# Cuentas",default=0)
    wizard_id=fields.Many2one("account.payment.request.wizard","Asistente",ondelete="cascade")
    request_id=fields.Many2one("account.payment.request","Solicitud",ondelete="cascade")
    type = fields.Selection(related="request_id.type", store=False, readonly=True)
    partner_id = fields.Many2one(related="request_id.partner_id", store=False, readonly=True)
    company_id = fields.Many2one(related="request_id.company_id", store=False, readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)

    document_ref = fields.Html(related="request_id.document_ref", store=False, readonly=True)

    pending=fields.Monetary("Pendiente",required=True,digits=(16,2))
    amount = fields.Monetary("Por Pagar", required=True, digits=(16, 2))
    bank_account_id = fields.Many2one("res.partner.bank", "Cuenta de Banco", required=False)

    is_prepayment=fields.Boolean("Es Anticipo",default=False)
    prepayment_account_id = fields.Many2one("account.account", "Cuenta Contable", required=False,domain=[('account_type','=','asset_prepayments'),('deprecated','=',False),('prepayment_account','=',True)])
    comments=fields.Text("Glosa")

    payment_account_id = fields.Many2one("account.account", "Cuenta Contable Pago Proveedor",
                                         compute="_compute_payment_account_id", store=True, readonly=True)

    lock_account=fields.Boolean("Bloquear Cuenta",default=False)

    @api.depends('request_id.partner_id', 'request_id.invoice_line_id', 'request_id.invoice_id', 'request_id.payment_employee_id','is_prepayment','prepayment_account_id', 'request_id.enable_other_account')
    def _compute_payment_account_id(self):
        for record in self:
            payment_account_id = record.request_id.partner_id.property_account_payable_id and record.request_id.partner_id.property_account_payable_id.id or False
            if record.request_id.type in ('purchase.order', 'request'):
                if record.request_id.enable_other_account:
                    payment_account_id=record.request_id.other_account_id.id
                else:
                    if record.is_prepayment:
                        payment_account_id = record.prepayment_account_id and record.prepayment_account_id.id or False
            if record.request_id.type == 'account.move':
                if record.request_id.invoice_line_id:
                    payment_account_id = record.request_id.invoice_line_id.account_id and record.request_id.invoice_line_id.account_id.id or False
                else:
                    if record.request_id.invoice_id:
                        payable_line = record.request_id.invoice_id.line_ids.filtered(
                            lambda
                                line: line.partner_id == record.request_id.partner_id and line.account_id.account_type == 'liability_payable'
                        )
                        if payable_line:
                            payment_account_id = payable_line[0].account_id.id
            if record.request_id.type == 'hr.employee.payment':
                if record.request_id.payment_employee_id:

                    payment_account_id = record.request_id.payment_employee_id.move_ids.filtered(lambda x: x.debit>0).mapped('account_id')#x.partner_id== record.request_id.partner_id

            if record.request_id.type == 'hr.employee.liquidation':
                if record.request_id.liquidation_employee_id:
                    payment_account_id = record.request_id.liquidation_employee_id.company_id.get_payment_conf().liquidation_account_id
            record.payment_account_id = payment_account_id

    @api.constrains('amount', 'pending')
    def _check_amount_limits(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError("El monto pagado debe ser mayor a 0.Ver Sol. %s , %s" % (record.request_id.id, record.request_id.name))
            if record.amount > record.pending:
                raise ValidationError(
                    "El monto pagado no puede ser mayor al valor pendiente.Ver Sol. %s , %s" % (record.request_id.id, record.request_id.name))

    @api.onchange('amount')
    def _onchange_amount(self):
        if self.amount <= 0:
            return {
                'warning': {
                    'title': "Valor inválido",
                    'message': "El monto pagado debe ser mayor a 0.",
                }
            }
        if self.amount > self.pending:
            return {
                'warning': {
                    'title': "Valor inválido",
                    'message': "El monto pagado no puede ser mayor al valor pendiente.",
                }
            }

    @api.depends('amount', 'pending')
    def _compute_amount_validation(self):
        for record in self:
            if not (0 < record.amount <= record.pending):
                raise ValidationError("El monto pagado debe ser mayor a 0 y menor o igual al valor pendiente.")