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
from odoo import SUPERUSER_ID

class AccountPaymentReportsWizard(models.Model):
    _name = 'account.payment.reports.wizard'
    _description = "Asistente de Reportes para Pagos/Cobros"

    @api.model
    def get_default_date_from(self):
        today = fields.Date.context_today(self)
        date_from = today + relativedelta(months=-1)
        return date_from

    @api.model
    def get_default_date_to(self):
        today = fields.Date.context_today(self)
        return today

    company_ids = fields.Many2many(
        "res.company",
        "payment_reports_wizard_rel",
        "wizard_id",
        "company_id",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company,
    )
    date_from=fields.Date("Fecha Inicio",required=True,default=get_default_date_from)
    date_to = fields.Date("Fecha Fin", required=True,default=get_default_date_to)
    type_report=fields.Selection([('pagos','Pagos'),
                                  ('oc_pagos','Orden de Compra con Pagos'),
                                  ('solicitudes_pagos','Solicitudes de Pagos'),
                                  ('resumen_sol_pagos', 'Resumen de OC con Pagos'),
                                  ('resumen_pagos_macros', 'Reporte de Pagos a Proveedores desde Bancos'),
                                  ('contratos','Reporte de Contratos por Cobrar'),
                                  ('pagos_proveedores','Reporte de Proveedores')
                                  ],"Tipo Informe",default="pagos")
    weeks=fields.Integer('# Semanas',default=None)

    type_report_partner=fields.Selection([('facturas','Facturas'),
                                          ('pagos', 'Pagos')
                                          ],string="Tipo de Reporte",default="facturas")

    partner_ids=fields.Many2many("res.partner","report_acct_payment_partner_rel","wizard_id","payment_id","Proveedores")

    type_payment=fields.Selection([('file','Reporte'),('summary','Resumen')],string="Tipo",default="file")

    contratista=fields.Boolean('Contratista',default=False)

    def validate_range_days(self):
        return True

    def process(self):
        self = self.with_context({"no_raise": True})
        self = self.with_user(SUPERUSER_ID)
        REPORTS = {
           "pagos": "gps_bancos.report_pagos_report_xlsx_act",
            "oc_pagos": "gps_bancos.report_oc_pagos_report_xlsx_act",
            'solicitudes_pagos':"gps_bancos.report_soli_pagos_report_xlsx_act",
            'resumen_sol_pagos': "gps_bancos.report_resumen_pagos_report_xlsx_act",
            'resumen_pagos_macros': "gps_bancos.report_resumen_pagos_macros_report_xlsx_act",
            'contratos': "gps_bancos.report_resumen_contratos_report_xlsx_act",
            'pagos_proveedores_facturas':'gps_bancos.report_facturas_proveedores_report_xlsx_act',
            'pagos_proveedores_pagos': 'gps_bancos.report_pagos_proveedores_report_xlsx_act'
        }
        REPORT=""
        for brw_each in self:
            try:
                brw_each.validate_range_days()
                type_report=brw_each.type_report
                if brw_each.type_report=="pagos_proveedores":
                    type_report+="_"+brw_each.type_report_partner
                    if brw_each.type_payment == "summary":
                        domain=[
                            ('company_id','=',brw_each.company_ids.ids),
                            ('bank_macro_id.state','=','done'),
                            ('date_payment','>=',brw_each.date_from),
                            ('date_payment','<=',brw_each.date_to),

                        ]
                        act_name="gps_bancos.action_account_payment_bank_macro_summary"
                        if brw_each.contratista:
                            rp_contratista_id = self.env.ref('gps_bancos.rp_contratista').id
                            domain+= [('partner_id.category_id','=',rp_contratista_id)]
                            act_name = "gps_bancos.action_account_payment_bank_macro_summary_contratista"
                        if brw_each.partner_ids:
                            domain+=[('partner_id','in',brw_each.partner_ids.ids)]
                        srch_payments_summary=self.env["account.payment.bank.macro.summary"].sudo().search(domain)
                        if not srch_payments_summary:
                            raise ValidationError(_("No hay resultados con los parametros consultados"))

                        action = self.env.ref(act_name).read()[0]
                        action['domain'] = [('id', 'in', srch_payments_summary.ids)]
                        return action

                OBJ_REPORTS = self.env[self._name].sudo()
                context = dict(active_ids=[brw_each.id],
                               active_id=brw_each.id,
                               active_model=self._name,
                               landscape=True
                               )
                OBJ_REPORTS = OBJ_REPORTS.with_context(context)
                REPORT = REPORTS[type_report]
                report_value = OBJ_REPORTS.env.ref(REPORT).with_user(SUPERUSER_ID).report_action(OBJ_REPORTS)
                report_value["target"] = "new"
                return report_value
            except Exception as e:
                raise ValidationError(_("Error al Imprimir %s -- %s") % (REPORT, str(e),))