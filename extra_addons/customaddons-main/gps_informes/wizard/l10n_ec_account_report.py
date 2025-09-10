# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _,SUPERUSER_ID
import base64
from xml.etree.ElementTree import Element, SubElement, tostring
from ...message_dialog.tools import FileManager
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager
fileO=FileManager()        
dateO=DateManager()
calendarO=CalendarManager()

REPORT_DICT_VALUES= {
    'flujo_caja':'gps_informes.report_flujo_caja_report_xlsx_act',
    'vencidos_pagar':'gps_informes.report_vencidos_pagar_report_xlsx_act',
    'cuentas_pagar':'gps_informes.report_cuentas_pagar_report_xlsx_act',
    'pagos_anticipados':'gps_informes.report_pagos_anticipados_report_xlsx_act',
    'cobros_anticipados':'gps_informes.report_cobros_anticipados_report_xlsx_act'
}

class L10nEcAccountReport(models.TransientModel):
    _name = "l10n_ec.account.report"
    _description = "Reportes Financieros"
    
    @api.model
    def get_default_company_ids(self):
        if self._context.get("allowed_company_ids", []):
            return self._context.get("allowed_company_ids", [])
        return [self.env["res.users"].browse(self._uid).company_id.id]

    @api.model
    def get_default_range_days(self):
        if self._context.get("default_type_report", '') in ('vencidos_pagar','pagos_anticipados'):
            return 30
        return 7

    company_ids=fields.Many2many("res.company","l10n_ec_account_report_company_rel","wizard_id","company_id","Compañias",default=get_default_company_ids)

    type_report = fields.Selection([('vencidos_pagar', 'Vencidos por Pagar'),
                                    ('pagos_anticipados', 'Pagos Anticipados'),
                                    ('cobros_anticipados', 'Cobros Anticipados'),
                                    ('cuentas_pagar', 'Cuentas por Pagar'),
                                    ('flujo_caja', 'Flujo de Caja')
                                    ],
                                   default='vencidos_pagar', copy=False,string="Tipo de Reporte")

    range_days=fields.Integer("Dias por Periodos",required=False,default=get_default_range_days)
    periods = fields.Integer("# Periodos", required=False, default=4)

    type_view_balance=fields.Selection([('with_balance','Solo Con saldos'),
                                    ('all','Todos')],string="Balance de Saldos",default="with_balance")

    date_from=fields.Date("Fecha Inicial")
    date_to = fields.Date("Fecha Final")

    @api.constrains('periods','periods')
    def validate_range_days(self):
        for brw_each in self:
            if brw_each.range_days<=0:
                raise   ValidationError(_("Dias por Periodos deben ser mayores a 0"))
            if brw_each.periods<=0:
                raise   ValidationError(_("Los # de Periodos deben ser mayores a 0"))

    def process_report(self):
        self = self.with_context({"no_raise": True})
        self = self.with_user(SUPERUSER_ID)
        for brw_each in self:
            try:
                brw_each.validate_range_days()
                OBJ_REPORTS= self.env[self._name].sudo()
                context = dict(active_ids=[brw_each.id],
                               active_id=brw_each.id,
                               active_model=self._name,
                               landscape=True
                               )
                REPORT = REPORT_DICT_VALUES[brw_each.type_report]
                OBJ_REPORTS = OBJ_REPORTS.with_context(context)
                report_value = OBJ_REPORTS.env.ref(REPORT).with_user(SUPERUSER_ID).report_action(OBJ_REPORTS)
                report_value["target"] = "new"
                return report_value
            except Exception as e:
                raise ValidationError(_("Error al Imprimir %s -- %s") % (REPORT, str(e),))