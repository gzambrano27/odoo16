# * - coding: utf - 8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class CalendarLegalHoliday(models.Model):
    _name = "calendar.legal.holiday"
    _description = "Días Festivos Legales"

    date_from=fields.Date("Fecha Inicio",required=True)
    date_to = fields.Date("Fecha Fin", required=True)
    holiday_id=fields.Many2one("calendar.holiday","Feriado",required=True)

    _rec_name="holiday_id"

    def get_holiday(self,date_from,date_to):
        self._cr.execute(""" select holiday_id 
from calendar_legal_holiday where %s>=date_from and %s<=date_to """,(date_from,date_to))
        result=self._cr.dictfetchone()
        return result
