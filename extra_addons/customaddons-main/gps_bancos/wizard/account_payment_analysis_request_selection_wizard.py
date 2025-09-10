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

class AccountPaymentAnalysisRequestSelectionWizard(models.Model):
    _name = 'account.payment.analysis.request.selection.wizard'
    _description = "Asistente de Seleccion de Contactos "

    @api.model
    def _get_default_company_id(self):
        active_ids=self._context.get("active_ids",[])
        if active_ids:
            brw_wizard=self.env["account.payment.analysis.request.wizard"].browse(active_ids)
            return brw_wizard.company_id and brw_wizard.company_id.id or False
        return False

    @api.model
    def _get_default_request_id(self):
        active_ids = self._context.get("active_ids", [])
        return active_ids and active_ids[0] or False

    @api.model
    def _get_default_filter_docs(self):
        active_ids = self._context.get("active_ids", [])
        if active_ids:
            brw_wizard = self.env["account.payment.analysis.request.wizard"].browse(active_ids)
            return brw_wizard.filter_docs and brw_wizard.filter_docs or ''
        return False

    @api.model
    def get_default_date_from(self):
        active_ids = self._context.get("active_ids", [])
        if active_ids:
            brw_wizard = self.env["account.payment.analysis.request.wizard"].browse(active_ids)
            return brw_wizard.date_from
        return False

    @api.model
    def get_default_date_to(self):
        active_ids = self._context.get("active_ids", [])
        if active_ids:
            brw_wizard = self.env["account.payment.analysis.request.wizard"].browse(active_ids)
            return brw_wizard.date_to
        return False

    @api.model
    def get_default_selected_line_ids(self):
        active_ids = self._context.get("active_ids", [])
        if active_ids:
            brw_wizard = self.env["account.payment.analysis.request.wizard"].browse(active_ids)
            return brw_wizard.line_ids and brw_wizard.line_ids.ids or []
        return False


    date_from = fields.Date("Fecha Inicio", required=False, default=get_default_date_from)
    date_to = fields.Date("Fecha Fin", required=False, default=get_default_date_to)

    @api.model
    def _get_default_show_options(self):
        active_ids = self._context.get("active_ids", [])
        if active_ids:
            brw_wizard = self.env["account.payment.analysis.request.wizard"].browse(active_ids)
            return brw_wizard.show_options
        return 'show_lines'

    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,default=_get_default_company_id
    )
    request_id=fields.Many2one("account.payment.analysis.request.wizard","Solicitud",default=_get_default_request_id)
    partner_id=fields.Many2one("res.partner", "Proveedor")
    line_ids=fields.Many2many("account.move.line","account_move_line_pay_analysis_request_sel_rel","wizard_id","line_id","Detalle")
    move_ids = fields.Many2many("account.move", "account_movepay_analysis_request_sel_rel", "wizard_id",
                                "move_id", "Detalle")

    filter_docs = fields.Selection([('*', 'Todas'), ('03', 'Liquidaciones')], string="Filtrar por Tipo", default=_get_default_filter_docs)
    show_options = fields.Selection([('show_lines', 'Mostrar Lineas Contables por Vencimiento'),
                                     ('show_invoices', 'Mostrar Documentos por Vencimiento')
                                     ], default=_get_default_show_options, string="Forma de Busqueda")

    selected_line_ids = fields.Many2many("account.move.line", "account_move_line_sel_analysis_req_rel", "wizard_id",
                                "line_id", "Detalle",default=get_default_selected_line_ids)

    request_ids=fields.Many2many('account.payment.request' ,"acct_pay_request_analysis_req_rel", "wizard_id",
                                "request_id", "Solicitudes")

    _rec_name="partner_id"

    _order="id desc"

    @api.onchange('request_id')
    def onchange_request_id(self):
        pass
        # if self.request_id.filter_by_bank:
        #     filter_partner_ids=self.get_filtered_partners()
        #     filter_partner_ids+=[-1,-1]
        #     return {
        #             "domain":{
        #                 "partner_ids":[('id','in',filter_partner_ids)]
        #             }
        #         }

    def get_filtered_partners(self):
        # if self.request_id.filter_by_bank:
        #     filter_bank_ids = self.request_id.filter_bank_ids.ids
        #     if filter_bank_ids:
        #         filter_partner_ids = self.env["res.partner"].sudo().search(
        #             [('enable_payment_bank_ids', 'in', filter_bank_ids)])
        #         return filter_partner_ids.ids
        return []

    @api.onchange('partner_id','date_from','date_to')
    def onchange_partner_id(self):
        self.line_ids=[(6,0,[])]
        self.move_ids = [(6, 0, [])]
        srch=self.env["account.payment.request"].sudo().search([('company_id','=',self.company_id.id),
                                                                ('state','not in',('cancelled','locked','done')),
                                                                ('partner_id','=',self.partner_id.id),
                                                                ('type','=','account.move'),
                                                                ])
        invoice_line_ids = srch.mapped('invoice_line_id').filtered(lambda x: x.amount_residual != 0.00)
        invoice_line_ids += srch.mapped('invoice_line_ids').filtered(lambda x: x.amount_residual != 0.00)

        srch_lines=self.env["account.payment.analysis.request.wizard"].sudo().search([('company_id','=',self.company_id.id),
                                                                                           ('state','=','draft'),
                                                                                           ('checked','=',True)])
        invoice_line_ids += srch_lines.mapped('request_line_ids.invoice_line_id').filtered(lambda x: x.amount_residual != 0.00)
        CONTEXT_FILTER = {
            "show_for_payment": True,
            "default_company_id": self.company_id.id,
            'default_date_from': self.date_from,
            'default_date_to': self.date_to,
            'partner_ids': self.partner_id and [self.partner_id.id] or self.get_filtered_partners(),
            'default_show_options': self.show_options,
            'filter_docs': self.filter_docs,
            'selected_line_ids': self.request_id.line_ids.ids,
            "not_show_ids":invoice_line_ids and invoice_line_ids.ids or []
        }
        self.request_ids=srch and [(6,0,srch.ids)] or [(6,0,[])]
        if self.show_options=='show_lines':#lineas d easientos
            OBJ_LINE=self.env["account.move.line"].with_context(CONTEXT_FILTER)
            domain=OBJ_LINE._where_cal(domain=None)
            return {
                "domain":{'line_ids':domain}
            }
        else:#asientos
            OBJ_MOVE = self.env["account.move"].with_context(CONTEXT_FILTER)
            domain = OBJ_MOVE._where_cal(domain=None)
            return {
                "domain": {'move_ids': domain}
            }


    def process(self):
        self.ensure_one()
        line_ids=self.env["account.move.line"]
        if self.show_options=='show_lines':
            if not self.line_ids:
                raise ValidationError(_("Debes seleccionar al menos un registro para continuar"))
            line_ids=self.line_ids
        else:
            if not self.move_ids:
                raise ValidationError(_("Debes seleccionar al menos un registro para continuar"))
            line_ids=self.move_ids.mapped('line_ids').filtered(lambda line: line.account_id.account_type == 'liability_payable' and line.amount_residual != 0.00)
        self.request_id.line_ids = [(4, line.id) for line in line_ids]
        request_line_ids=[]
        DEC=2
        for brw_line in line_ids:
            request_line_ids.append((0,0,{
               "invoice_line_id":brw_line.id,
                "amount":round(-1.00*brw_line.amount_residual,DEC),

            }))
        self.request_id.request_line_ids=request_line_ids
        self.request_id.test_lines()
        return True