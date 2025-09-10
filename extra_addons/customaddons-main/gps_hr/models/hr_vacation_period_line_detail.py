from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...calendar_days.tools import CalendarManager, DateManager, MonthManager

dtObj = DateManager()

class HrVacationPeriodLineDetail(models.Model):
    _name = "hr.vacation.period.line.detail"
    _description = "Subdetalle Mensual de Periodo de vacaciones"

    period_id = fields.Many2one("hr.vacation.period", "Periodo de Vacaciones", ondelete="cascade")
    request_id = fields.Many2one("hr.leave", "Solicitud", ondelete="cascade")
    payslip_id = fields.Many2one("hr.payslip", "Rol")
    line_id = fields.Many2one("hr.vacation.period.line", "Detalle", ondelete="cascade")
    days = fields.Integer("Dia(s)", required=True, default=0)
    date_start = fields.Date(string="Fecha de Inicio")
    date_stop = fields.Date(string="Fecha de Fin")

    year = fields.Integer(string="Año", compute="_compute_year_month", store=True)
    month = fields.Integer(string="Mes", compute="_compute_year_month", store=True)


    @api.depends('date_start')
    def _compute_year_month(self):
        for record in self:
            if record.date_start:
                record.year = record.date_start.year
                record.month = record.date_start.month
            else:
                record.year = 0
                record.month = 0

    @api.model
    def search_between_dates(self, date_from, date_to,contract_id):
        """
        Devuelve ausencias que se superpongan con un rango de fechas dado.
        Considera que las ausencias pueden extenderse entre meses,
        mientras que el rango de fechas está dentro del mismo mes.
        """
        return self.search([
            ('request_id.contract_id', '=', contract_id),
            ('date_start', '<=', date_to),
            ('date_stop', '>=', date_from)
        ])
