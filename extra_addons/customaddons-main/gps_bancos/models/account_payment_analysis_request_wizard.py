from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime,date
from dateutil.relativedelta import relativedelta

from ...calendar_days.tools import DateManager,CalendarManager
from ...message_dialog.tools import FileManager
dtObj=DateManager()
calendarO=CalendarManager()
fileO=FileManager()
from datetime import datetime, timedelta
import re

class AccountPaymentAnalysisRequestWizard(models.Model):
    _name = 'account.payment.analysis.request.wizard'
    _description = "Asistente de Analisis de Pagos"

    @api.model
    def _get_default_checked(self):
        default_checked = self._context.get('default_checked', True)
        return default_checked

    @api.model
    def _get_default_request_type_id(self):
        code=self._context.get('type_code',False)
        if not code:
            return False
        srch=self.env["account.payment.request.type"].sudo().search([('code','=',code)])
        return srch and srch.id or False

    @api.model
    def get_default_date_from(self):
        today = fields.Date.context_today(self)
        date_from = today + relativedelta(months=-3)
        return date_from

    @api.model
    def get_default_date_to(self):
        today = fields.Date.context_today(self)
        OBJ_CONFIG=self.env["account.configuration.payment"].sudo()

        brw_conf = OBJ_CONFIG.search([
            ('company_id', '=', self.env.company.id)
        ])
        x = CalendarManager()
        v = x.dow(today)
        if brw_conf.day_id.value == v:
            return today
        else:
            fecha_actual=today
            while True:
                if calendarO.dow(fecha_actual) == brw_conf.day_id.value:
                    return fecha_actual
                fecha_final = fecha_actual + timedelta(days=1)
                fecha_actual = fecha_final

    @api.model
    def _get_default_date_request(self):
        return fields.Date.context_today(self)

    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company,
    )
    date_from=fields.Date("Fecha Inicio",required=True,default=get_default_date_from)
    date_to = fields.Date("Fecha Fin", required=True,default=get_default_date_to)

    date_range_display = fields.Char(string="Rango de Fechas", compute="_compute_date_range_display")

    filter_docs=fields.Selection([('*','Todas'),('03','Liquidaciones')],string="Filtrar por Tipo",default="*")

    @api.depends('date_from', 'date_to')
    @api.onchange('date_from', 'date_to')
    def _compute_date_range_display(self):
        for record in self:
            if record.date_from and record.date_to:
                record.date_range_display = f"Desde {record.date_from.strftime('%d/%m/%Y')} hasta {record.date_to.strftime('%d/%m/%Y')}"
            else:
                record.date_range_display = ''

    show_options=fields.Selection([('show_lines','Mostrar Lineas Contables por Vencimiento'),
                                   ('show_invoices','Mostrar Documentos por Vencimiento')
                                   ],default="show_lines",string="Forma de Busqueda")

    partner_ids=fields.Many2many("res.partner",compute="_compute_all_move_ids",store=False,readony=True,string="Proveedores")
    move_ids = fields.Many2many("account.move","acct_payment_analysis_move_req_wizard_rql",
                              "wizard_id","move_id",compute="_compute_all_move_ids",  store=False, readony=True,
                                string="Asientos")

    line_ids=fields.Many2many("account.move.line","acct_payment_analysis_move_linereq_wizard_rql",
                              "wizard_id","move_line_id",compute="_compute_all_move_ids",  store=True, readony=True,
                            string=  "Cuotas")

    date_request=fields.Date("Fecha de Solicitud",default=_get_default_date_request)

    filter_by_bank=fields.Boolean("Filtrar por Bancos",default=False)
    filter_bank_ids = fields.Many2many("res.bank", "acct_payment_filter_analysis_bank_req_wizard_rql",
                                       "wizard_id", "bank_id",
                                       "Bancos")

    state=fields.Selection([('draft','Preliminar'),
                            ('process','Procesado')
                            ],string="Estado",default="draft")
    date_process=fields.Datetime('Fecha de Procesado')

    request_ids=fields.One2many('account.payment.request','request_wizard_id','Sol. de Generacion')
    request_type_id=fields.Many2one('account.payment.request.type',"Motivo de Solicitud",required=True,default=_get_default_request_type_id)
    comments=fields.Char("Mensaje Adicional")

    currency_id=fields.Many2one(related="company_id.currency_id",store=False,readonly=True)
    total=fields.Monetary('Total por Pagar',compute="_compute_resumen",store=True,readonly=True)
    count_lines = fields.Integer('# Cuotas', compute="_compute_resumen", store=True, readonly=True)
    count_partner = fields.Integer('# Proveedores', compute="_compute_resumen", store=True, readonly=True)
    count_invoices = fields.Integer('# Facturas', compute="_compute_resumen", store=True, readonly=True)

    request_line_ids=fields.One2many('account.payment.analysis.request.line.wizard','request_wizard_id','Detalle')

    checked=fields.Boolean('Revisado',default=_get_default_checked)

    def action_set_checked(self):
        for brw_each in self:
            if not brw_each.request_line_ids:
                raise ValidationError(_("Debes seleccionar al menos una linea"))
            if brw_each.total<=0.00:
                raise ValidationError(_("El valor debe ser mayor a 0.00"))
            brw_each.write({"checked":True})
        return True

    def action_set_not_checked(self):
        for brw_each in self:
            brw_each.write({"checked":False})
        return True

    def get_filter_account_ids(self):
        brw_request=self.ensure_one()
        domain=[('account_type', '=', 'liability_payable'),
                ('company_id', '=', brw_request.company_id.id)]
        param_value = self.env['ir.config_parameter'].sudo().get_param('filter.account.name')
        if brw_request.request_type_id == self.env.ref('gps_bancos.req_type_caja_chica'):
            if param_value in ('True', '1'):
                domain+= [ ('name', 'ilike', 'CAJA CHICA%')]
        elif brw_request.request_type_id == self.env.ref('gps_bancos.req_type_reembolso'):
            if param_value in ('True', '1'):
                domain+= [ ('name', 'ilike', 'REEMBOLSO%')]
        else:
            domain += [
                ('name', 'not ilike', 'CAJA CHICA%'),
                ('name', 'not ilike', 'REEMBOLSO%')
            ]
        srch=self.env["account.account"].search(domain)
        return srch and srch.ids or [-1,-1]

    @api.depends('line_ids','request_line_ids','state')
    def _compute_resumen(self):
        DEC=2
        for brw_each in self:
            if brw_each.state=='draft':
                total=round(abs(sum(brw_each.request_line_ids.mapped('amount'))),DEC)
                brw_each.total = total
                brw_each.count_lines = len(brw_each.line_ids)
                brw_each.count_partner = len(brw_each.partner_ids)
                brw_each.count_invoices = len(brw_each.move_ids)

    @api.depends('request_line_ids')
    def _compute_all_move_ids(self):
        for brw_each in self:
            move_ids=brw_each.request_line_ids.mapped('invoice_line_id.move_id')
            line_ids = brw_each.request_line_ids.mapped('invoice_line_id')
            partner_ids = brw_each.request_line_ids.filtered(lambda x: x.partner_id).mapped('partner_id')
            brw_each.move_ids=move_ids
            brw_each.line_ids = line_ids
            brw_each.partner_ids = partner_ids


    @api.depends('request_type_id.name','request_type_id','comments')
    def _compute_full_name(self):
        for record in self:
            full_name=str(record.id)
            if record.request_type_id:
                full_name = f"SOL. # {record.id} POR {record.request_type_id.name}"
            else:
                if record.id:
                    full_name = f"SOL. # {record.id}"
            if record.comments:
                full_name=full_name+","+record.comments
            record.full_name=full_name

    _rec_name="full_name"

    full_name = fields.Char(string='Nombre Completo', compute='_compute_full_name', store=True,readonly=True)

    @api.onchange('company_id','date_from', 'date_to', 'partner_ids')
    def onchange_params(self):
        self.line_ids = [(6, 0, [])]
        self.move_ids = [(6, 0, [])]
        self.partner_ids = [(6, 0, [])]


    def unlink(self):
        for brw_each in self:
            if brw_each.state != 'draft':
                raise ValidationError(_("No puedes borrar un registro que no sea preliminar"))
            if brw_each.request_type_id in (self.env.ref('gps_bancos.req_type_reembolso'),self.env.ref('gps_bancos.req_type_caja_chica')):
                if brw_each.state == 'draft' and brw_each.checked:
                    raise ValidationError(_("No puedes borrar un registro que esta validado"))
        return super(AccountPaymentAnalysisRequestWizard, self).unlink()

    def process(self):
        DEC=2
        OBJ_CONFIG = self.env["account.configuration.payment"].sudo()
        OBJ_REQUEST=self.env["account.payment.request"]
        self.ensure_one()
        if not self.move_ids and not self.line_ids:
            raise ValidationError(_("Debes seleccionar al menos un documento"))
        brw_conf = OBJ_CONFIG.search([
            ('company_id', '=', self.company_id.id)
        ])
        if not brw_conf:
            raise ValidationError(_("No hay configuracion de pagos para la empresa %s") % (self.company_id.name,))
        request_ids = OBJ_REQUEST
        #####
        quotas={}
        for brw_request_line in self.request_line_ids:
            if brw_request_line.amount_residual !=0.00:
                if brw_request_line.amount<0.00:
                    raise ValidationError(_("No puedes aplicar un valor mayor al credito.Revisa documento %s ") % (
                        brw_request_line.move_id.name,))
                if brw_request_line.amount>brw_request_line.amount_residual:
                    raise ValidationError(_("No puedes aplicar un valor mayor al saldo.Revisa documento %s ") % (brw_invoice_line.move_id.name,))
                if brw_request_line.amount>abs(brw_request_line.credit):
                    raise ValidationError(_("No puedes aplicar un valor mayor al credito.Revisa documento %s ") % (brw_invoice_line.move_id.name,))
                brw_invoice_line=brw_request_line.invoice_line_id
                if not quotas.get(brw_invoice_line.move_id,False):
                    quotas[brw_invoice_line.move_id]  = brw_invoice_line.move_id._compute_quota()
                type_document='quota'
                DOMAIN = [('company_id', '=', self.company_id.id),
                              ('type_document','=',type_document),
                              ('type', '=', 'account.move'),
                              ('invoice_line_id', '=', brw_invoice_line.id),
                              ]
                DOMAIN+=[('state','not in',('cancelled','locked','done'))]
                srch=OBJ_REQUEST.search(DOMAIN)

                date_maturity =brw_invoice_line.date_maturity or brw_invoice_line.move_id.date or brw_invoice_line.move_id.invoice_date or fields.Date.context_today(self)

                quota=quotas[brw_invoice_line.move_id].get(brw_invoice_line,0)
                percentage = 0.0
                if brw_invoice_line.move_id.move_type in (
                'in_invoice', 'in_receipt') and brw_invoice_line.move_id.amount_total > 0.00:
                    percentage = round((abs(brw_invoice_line.credit) / brw_invoice_line.move_id.amount_total) * 100.0, DEC)
                    percentage = min(percentage, 100.00)
                vals = {
                    "company_id": self.company_id.id,
                    'type_document':type_document,
                    "invoice_id": brw_invoice_line.move_id.id,
                    "invoice_line_id": brw_invoice_line.id,
                    "invoice_line_ids":[(6,0, [brw_invoice_line.id])] ,
                    "payment_term_id":brw_invoice_line.move_id.invoice_payment_term_id.id,
                    "quota": quota,
                    "date_maturity":  date_maturity,
                    "partner_id": brw_invoice_line.partner_id.id,
                    "amount_original":  round(abs(brw_invoice_line.amount_residual),DEC),
                    "amount":round(abs( brw_request_line.amount),DEC),
                    "state": "draft",
                    "type": "account.move",
                    'origin':'automatic',
                    'temporary': True,
                    "description_motive":"CUOTA %s DE %s" % (quota,brw_invoice_line.move_id.name),
                    'checked':True,
                    'request_wizard_id':self.id,
                    'request_type_id': self.request_type_id.id,
                    "percentage":percentage,
                    'document_ref':brw_invoice_line.move_id.ref,
                    'default_mode_payment':brw_request_line.default_mode_payment,
                }
                date = self.env["purchase.order"].obtener_fecha_proximo_dia(date_maturity,
                                                                             brw_conf.day_id.value)
                vals["date"] = date
                vals["is_prepayment"] = False
                if not srch:
                    brw_request = self.env["account.payment.request"].create(vals)
                    brw_request.action_confirmed()
                    request_ids+=brw_request
                else:
                    if srch.state=='draft':
                        srch.write(vals)
                        srch.action_confirmed()
                    request_ids += srch
        action = self.env["ir.actions.actions"]._for_xml_id("gps_bancos.account_payment_request_view_action")
        context = {'search_default_is_oc': 1, 'search_default_is_move': 1, 'search_default_is_draft': 1,
                   'search_default_is_confirmed': 1, 'hide_parent': False}
        action["name"]="Solicitud de Pagos OC y Facturas"
        action["context"] = context
        request_list_ids=request_ids and request_ids.ids or []
        request_list_ids+=[-1,-1]
        action["domain"] = [('id','in',tuple(request_list_ids))]
        self.write({"state":"process","date_process":fields.Datetime.now()})
        return action

    _order="id desc"

    _check_company_auto = True

    def action_open_requests(self):
        self.ensure_one()
        requests = self.env["account.payment.request"].sudo().search([('request_wizard_id','=',self.id)])
        requests_ids = requests.ids + [-1, -1]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "gps_bancos.account_payment_request_view_action"
        )
        action["domain"] = [('id', 'in', requests_ids)]
        return action

    def action_open_invoices(self):
        self.ensure_one()
        invoices_lines = self.line_ids.ids
        invoices_lines = invoices_lines.ids + [-1, -1]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_in_invoice_type"
        )
        action["domain"] = [('id', 'in', invoices_lines)]
        return action

    def extraer_doc_y_numero(self,texto):

        match = re.search(r'^(.*?)\s+\d{3}-\d{3}-(\d+)$', texto)
        if match:
            nombre = match.group(1)  # Todo antes del primer bloque de números
            numero = int(match.group(2))  # Últimos dígitos sin ceros a la izquierda
            return f"{nombre} {numero}"
        return texto  # Devuelve el original si no coincide

    def test_lines(self):
        for brw_each in self:
            for brw_line in brw_each.request_line_ids:
                brw_line._compute_analize_accounts()

    def action_export_lote_excel(self):
        self.ensure_one()
        return self.env.ref('gps_bancos.report_lote_sol_cxp_report_xlsx_act').report_action(self)
