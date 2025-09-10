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

REPORT_DICT_VALUES= {
    'cargas_familiares':'gps_hr.report_employee_cargas_familiares_report_xlsx_act',
    'cumpleanios':'gps_hr.report_employee_cumpleanios_report_xlsx_act',
}

class HrEmployeeReportWizard(models.TransientModel):
    _name = "hr.employee.report.wizard"
    _description = "Reportes de Empleados"

    company_ids = fields.Many2many("res.company", "hr_employee_report_wizard_empl_rel","wizard_id","employee_id","Compañias")
    type_report = fields.Selection([('cumpleanios', 'FECHAS DE CUMPLEAÑOS'),
                                    ('cargas_familiares', 'CARGAS FAMILIARES')
                                    ], default='cumpleanios', copy=False)

    def process_report(self):
        REPORT = self._context.get('default_report', '')
        self = self.with_context({"no_raise": True})
        self = self.with_user(SUPERUSER_ID)
        for brw_each in self:
            try:
                OBJ_REPORTS = self.env[self._name].sudo()
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

    # endregion

