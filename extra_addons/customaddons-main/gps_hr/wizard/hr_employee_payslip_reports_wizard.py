# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID
import base64
from xml.etree.ElementTree import Element, SubElement, tostring
from ...message_dialog.tools import FileManager
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager

fileO = FileManager()
dateO = DateManager()
calendarO = CalendarManager()

REPORTS={
    'payslip':'gps_hr.report_payslip_runs_report_xlsx_act',
    'movements': 'gps_hr.report_payslip_movements_report_xlsx_act',

}

class hr_employee_payslip_reports_wizard(models.TransientModel):
    _name = "hr.employee.payslip.reports.wizard"
    _description = "Reportes de Nomina"

    @api.model
    def get_default_year(self):
        return fields.Date.today().year

    @api.model
    def get_default_month_id(self):
        month = fields.Date.today().month
        srch = self.env["calendar.month"].sudo().search([('value', '=', month)])
        return srch and srch[0].id or False

    company_id = fields.Many2one("res.company", "Compañia")

    type = fields.Selection([('payslip', 'Reportes de Nomina'),
                             ('movements', 'Reportes de Rubros')], default='payslip',string="Reporte", copy=False)

    year = fields.Integer("Año", default=get_default_year)
    month_id = fields.Many2one("calendar.month", "Mes", required=True, default=get_default_month_id)

    @api.model
    def get_default_date_start(self):
        if self._context.get("is_report", False):
            NOW = fields.Date.today()
            YEAR = NOW.year
            MONTH = NOW.month
            return dateO.create(YEAR, MONTH, 1).date()
        return None

    @api.model
    def get_default_date_end(self):
        if self._context.get("is_report", False):
            NOW = fields.Date.today()
            YEAR = NOW.year
            MONTH = NOW.month
            LAST_DAY = calendarO.days(YEAR, MONTH)
            return dateO.create(YEAR, MONTH, LAST_DAY).date()
        return None

    @api.model
    def _get_default_type_struct_id(self):
        srch = self.env["hr.payroll.structure.type"].sudo().search([])
        return srch and srch[0].id or False

    date_start = fields.Date("Fecha Inicial", required=True, store=True, readonly=False, default=get_default_date_start)
    date_end = fields.Date("Fecha Final", required=True, store=True, readonly=False, default=get_default_date_end)

    type_struct_id = fields.Many2one("hr.payroll.structure.type", "Tipo", required=False,
                                     default=_get_default_type_struct_id)

    employee_ids=fields.Many2many("hr.employee","payslips_wizard_employee_rel","wizard_id","employee_id","Empleados")
    rule_ids = fields.Many2many("hr.salary.rule", "payslips_wizard_rules_rel", "wizard_id", "salary_rule_id",
                                    "Rubros")

    payslip_type=fields.Selection([("rol","Rol"),
                                   ("finiquito","Finiquito"),
                                   ("*","Rol y Finiquito")],default="rol",string="Documentos")

    @api.onchange('year', 'month_id')
    def onchange_year_month(self):
        YEAR = self.year
        if self.month_id:
            MONTH = self.month_id.value

            LAST_DAY = calendarO.days(YEAR, MONTH)
            self.date_start = dateO.create(YEAR, MONTH, 1).date()
            self.date_end = dateO.create(YEAR, MONTH, LAST_DAY).date()
        else:
            self.date_start=None
            self.date_end = None

    def process_report(self):
        self = self.with_context({"no_raise": True})
        self = self.with_user(SUPERUSER_ID)
        REPORT=''
        for brw_each in self:
            try:
                data={}
                finiquito_ids=[]
                rol_ids=[]
                REPORT=REPORTS[brw_each.type]
                if REPORT=="gps_hr.report_payslip_runs_report_xlsx_act":
                    OBJ_REPORT_PAYSLIP = self.env["hr.payslip.run"].sudo()
                    srch_payslip_run = OBJ_REPORT_PAYSLIP
                    if brw_each.payslip_type in ('rol','*'):
                        domain=[('month_id','=',brw_each.month_id.id),
                                                                    ('year','=',brw_each.year),
                                                                    ('state','!=','cancelled')
                                                                    ]
                        if brw_each.company_id:
                            domain+= [('company_id', '=', brw_each.company_id.id) ]
                        if brw_each.type_struct_id:
                            domain += [('type_struct_id', '=', brw_each.type_struct_id.id)]

                        srch_payslip_run=OBJ_REPORT_PAYSLIP.search(domain)
                        rol_ids=srch_payslip_run and srch_payslip_run.ids or []
                    #####################################################################################################
                    OBJ_LIQUIDATION = self.env["hr.employee.liquidation"].sudo()
                    srch_liquidation=OBJ_LIQUIDATION
                    if brw_each.payslip_type in ('finiquito','*'):
                        domain = [('month_id', '=', brw_each.month_id.id),
                                  ('year', '=', brw_each.year),
                                  ('state', '!=', 'cancelled')
                                  ]
                        if brw_each.company_id:
                            domain += [('company_id', '=', brw_each.company_id.id)]

                        srch_liquidation = OBJ_LIQUIDATION.search(domain)
                        finiquito_ids=srch_liquidation and srch_liquidation.ids or []
                    if not srch_payslip_run and not srch_liquidation:
                        raise ValidationError(_("Sin resultados"))
                    print(srch_payslip_run)
                    print(srch_liquidation)
                    #####################################################################################################
                    context = dict(active_ids=srch_payslip_run.ids,
                                   active_id=srch_payslip_run and srch_payslip_run[0].id or 0,
                                   active_model=OBJ_REPORT_PAYSLIP._name,
                                   landscape=True,
                                   payslip_type=brw_each.payslip_type,
                                   finiquito_ids=finiquito_ids,
                                    rol_ids=rol_ids
                                   )

                    data={
                        "finiquito_ids": finiquito_ids,
                        "payslip_type": brw_each.payslip_type,
                        'rol_ids':rol_ids
                    }
                else:

                    rol_ids = [brw_each.ids]
                    context = dict(active_ids=[brw_each.id],
                                   active_id=brw_each.id,
                                   active_model=self._name,
                                   landscape=True,
                                   payslip_type=brw_each.payslip_type,
                                   finiquito_ids=finiquito_ids,
                                   rol_ids=rol_ids
                                   )
                OBJ_REPORTS = self.env[self._name].sudo()
                OBJ_REPORTS = OBJ_REPORTS.with_context(context)
                report_value = OBJ_REPORTS.env.ref(REPORT).with_user(SUPERUSER_ID).report_action(OBJ_REPORTS,data=data)
                report_value["target"] = "new"
                return report_value
            except Exception as e:
                raise ValidationError(_("Error al Imprimir %s -- %s") % (REPORT, str(e),))

    # endregion


