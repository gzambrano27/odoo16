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

class AccountPaymentAnalysisRequestWizard(models.Model):
    _name = 'account.payment.analysis.request.wizard'
    _description = "Asistente de Analisis de Pagos"

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
        date_from = today + relativedelta(months=-1)
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
        return self.get_default_date_to()

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
    filter_invoices=fields.Boolean('Filtrar por Facturas',default=False)
    filter_partners = fields.Boolean('Filtrar por Proveedores con saldos', default=True)
    #
    partner_ids=fields.Many2many("res.partner","acct_res_partner_wizard_rql",
                              "wizard_id","partner_id",
                              "Proveedores")

    line_ids=fields.Many2many("account.move.line","acct_payment_analysis_move_linereq_wizard_rql",
                              "wizard_id","move_line_id",
                              "Cuotas")

    move_ids = fields.Many2many("account.move", "acct_payment_analysis_move_req_wizard_rql",
                                "wizard_id", "move_id",
                                "Documentos")

    filter_move_ids = fields.Many2many("account.move", "acct_payment_filter_analysis_move_req_wizard_rql",
                                "wizard_id", "move_id",
                                "Documentos")
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
    request_type_id=fields.Many2one('account.payment.request.type',"Tipo",required=True,default=_get_default_request_type_id)
    comments=fields.Char("Mensaje Adicional")

    @api.depends('request_type_id.name')
    def _compute_full_name(self):
        for record in self:
            if record.request_type_id:
                record.full_name = f"SOL. # {record.id} POR {record.request_type_id.name}"
            else:
                record.full_name = f"SOL. # {record.id}"

    _rec_name="full_name"

    full_name = fields.Char(string='Nombre Completo', compute='_compute_full_name', store=True,readonly=True)

    @api.onchange('company_id','date_from', 'date_to', 'partner_ids')
    def onchange_params(self):
        self.line_ids = [(6, 0, [])]
        self.move_ids = [(6, 0, [])]
        self.filter_invoices = False

    @api.onchange('filter_partners','filter_by_bank','filter_bank_ids')
    def onchange_partners(self):
        self.partner_ids=[(6,0,[])]
        from datetime import date

        fecha_inicio = date(2024, 1, 1)
        fecha_fin = date(2030, 12, 31)
        if (self.filter_by_bank and self.filter_bank_ids )or self.filter_partners:
            context = {'filter_by_bank': self.filter_by_bank,
                       'filter_bank_ids': self.filter_by_bank and self.filter_bank_ids.ids or [],
                       'show_for_payment':self.filter_partners,
                       'default_company_id': self.company_id.id,
                       'default_date_from': fecha_inicio,
                       'default_date_to': fecha_fin,
                       'default_show_options': 'show_partners'}
            list_ids = self.env["res.partner"].sudo()._get_domain_list_ids(context)
            return {
                "domain":{"partner_ids":[('id','in',list_ids)]}
            }
        return {
            "domain": {"partner_ids": [('id', '!=', -1)]}
        }

    @api.onchange('filter_move_ids','filter_invoices','show_options','date_to','date_from')
    def onchange_filter_move_ids(self):
        self.line_ids=[(6,0,[])]
        if self.show_options=='show_lines' and self.filter_invoices and self.filter_move_ids:
            line_ids=self.filter_move_ids.line_ids.filtered(lambda x: x.amount_residual!=0 and
                                                                      x.credit>0
                                                                      and x.account_id.account_type== 'liability_payable'
                                                                      and  (
                                                                                  self.date_from <= x.date_maturity <= self.date_to)
                                                            )
            line_ids=line_ids and line_ids.ids or []
            self.line_ids = [(6, 0,line_ids)]

    def unlink(self):
        for brw_each in self:
            if brw_each.state != 'draft':
                raise ValidationError(_("No puedes borrar un registro que no sea preliminar"))
        return super(AccountPaymentAnalysisRequestWizard, self).unlink()

    def process(self):
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
        filter="moves"
        line_ids=self.move_ids and self.move_ids.ids or []
        if self.show_options == "show_lines":
            filter="lines"
            line_ids = self.line_ids and self.line_ids.ids or []
        line_ids+=[-1,-1]
        result=self.env["account.move"].sudo().search_query_moves(filter,line_ids)
        for each_result in result:
            type_document="document"
            DOMAIN=[('company_id','=',self.company_id.id),
                    ('type_document', '=', type_document),
                    ('type','=','account.move'),
                    ('invoice_id','=',each_result["invoice_id"]),
            ]
            if self.show_options=="show_lines":
                type_document='quota'
                DOMAIN = [('company_id', '=', self.company_id.id),
                          ('type_document','=',type_document),
                          ('type', '=', 'account.move'),
                          ('invoice_line_id', '=', each_result["invoice_line_id"]),
                          ]
            DOMAIN+=[('state','not in',('cancelled','locked'))]
            srch=OBJ_REQUEST.search(DOMAIN)
            #print([(6,0, each_result["invoice_line_ids"] or [each_result["invoice_line_id"] ])])
            vals = {
                "company_id": self.company_id.id,
                'type_document':type_document,
                "invoice_id": each_result["invoice_id"],
                "invoice_line_id": each_result["invoice_line_id"],
                "invoice_line_ids":[(6,0, each_result["invoice_line_ids"] or [each_result["invoice_line_id"] ])] ,
                "payment_term_id": each_result["invoice_payment_term_id"],
                "quota": each_result["quota"],
                "date_maturity": each_result["date_maturity"],
                "partner_id": each_result["partner_id"],
                "amount_original": each_result["amount_residual"],
                "amount": each_result["amount_residual"],
                "state": "draft",
                "type": "account.move",
                'origin':'automatic',
                'temporary': True,
                "description_motive":"CUOTA %s DE %s" % (each_result["quota"],each_result["invoice_name"]),
                'checked':True,
                'request_wizard_id':self.id,
                'request_type_id': self.request_type_id.id
            }
            date = self.env["purchase.order"].obtener_fecha_proximo_dia(each_result["date_maturity"],
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
        action["domain"] = [('date_maturity','>=',self.date_from),('date_maturity','<=',self.date_to),('id','in',tuple(request_list_ids))]
        self.write({"state":"process","date_process":fields.Datetime.now()})
        return action

    _order="id desc"

    _check_company_auto = True