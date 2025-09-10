# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from ...calendar_days.tools import CalendarManager, DateManager, MonthManager
from odoo.exceptions import ValidationError
dtObj=DateManager()

class HrVacationPeriodWizard(models.TransientModel):    
    _name="hr.vacation.period.wizard"
    _description="Asistente de Generacion de Periodo de Vacaciones"

    @api.model
    def get_default_company_id(self):
        brw_user = self.env["res.users"].browse(self._uid)
        return brw_user.company_id.id

    @api.model
    def get_year_start(self):
        return int((fields.Date.today()).year)

    @api.model
    def get_year_end(self):
        return int((fields.Date.today()).year) + 1

    company_id = fields.Many2one("res.company", "Empresa", default=get_default_company_id)
    year_start = fields.Integer("Año Inicial", required=True, default=get_year_start)
    year_end = fields.Integer("Año Final", required=True, default=get_year_end)
    employee_ids = fields.Many2many("hr.employee", "hr_vacation_period_wizard_rel", "wizard_id", "employee_id",
                                    string="Empleado(s)")

    @api.onchange("year_start", "year_end",'company_id')
    def onchange_year_endstart(self):
        now_year = int((fields.Date.today()).year)
        msg = False
        if self.year_start:
            self.year_start = abs(self.year_start)
        else:
            self.year_start = now_year

        if self.year_end:
            self.year_end = abs(self.year_end)
            if self.year_start > self.year_end:
                self.year_end = self.year_start + 1
                msg = _("El Año Inicial no puede ser mayor al Año Final")

        if (self.year_end - self.year_start) != 1:
            msg = _("Debe existir solo un periodo de diferencia entre los años seleccionados")
            self.year_end = self.year_start + 1

        values = {"value": {"year_start": self.year_start, "year_end": self.year_end, "employee_ids": [(6, 0, [])]}}
        self.env.cr.execute("""SELECT HE.ID, HE.NAME 
                                   FROM HR_EMPLOYEE HE
                                   INNER JOIN HR_CONTRACT HC ON HC.EMPLOYEE_ID = HE.ID
                                   INNER JOIN HR_CONTRACT_TYPE HCT ON HCT.ID=HC.CONTRACT_TYPE_id 
                                   LEFT JOIN HR_VACATION_PERIOD VP ON VP.CONTRACT_ID = HC.ID 
                                   AND VP.YEAR_START = %s AND VP.YEAR_END = %s
                                   WHERE HC.STATE='open' AND HC.company_id=%s
                                   AND (%s >= EXTRACT(YEAR FROM (HC.DATE_START)) 
                                   AND EXTRACT(YEAR FROM (HC.DATE_START)) <= %s)
                                   AND COALESCE(VP.LOCKED, FALSE) = FALSE 
                                   and COALESCE(hct.legal_iess ,FALSE) 
                                   ORDER BY HE.NAME ASC""",
                            (self.year_start, self.year_end, self.company_id.id,self.year_start, self.year_end))
        result = self.env.cr.fetchall()
        employee_ids = []
        if result:
            employee_ids = list(dict(result).keys())
            employee_ids+=[-1,-1]

        values["domain"] = {"employee_ids": [('id', 'in', tuple(employee_ids))]}

        if msg:
            values["warning"] = {"title": _("Error"), "message": msg}

        return values

    def process(self):
        OBJ_VACATION_PERIOD = self.env["hr.vacation.period"]
        OBJ_VACATION_PERIOD = OBJ_VACATION_PERIOD.with_context({"pass_validate": False})

        for brw_each in self:
            if not brw_each.employee_ids:
                raise ValidationError(_("Al menos un empleado debe ser seleccionado"))

            employee_ids = [brw_employee.id for brw_employee in brw_each.employee_ids]
            if (brw_each.year_end - brw_each.year_start) != 1:
                raise ValidationError(_("Debe existir solo un periodo de diferencia entre los años seleccionados"))

            OBJ_VACATION_PERIOD.create_periods(brw_each.company_id.id, brw_each.year_start, brw_each.year_end,
                                               employee_ids)

        return True
    
