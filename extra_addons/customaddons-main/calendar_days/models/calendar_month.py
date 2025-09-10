# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models,api
from ..tools import DateManager
dtObj=DateManager()

class CalendarMonth(models.Model):    
    _name="calendar.month"
    _description="Meses del Año"
    
    value=fields.Integer("Valor",required=True)
    name=fields.Char("Descripción",required=True)
    
    _sql_constraints = [("calendar_month_name_unique_name","unique(name)","Descripción debe ser única"),
                        ("calendar_month_name_unique_value","unique(value)","Valor debe ser único"),
                        ]
    
    _order="value asc"
    
    @api.model
    def get_month_name(self,value):
        srch=self.search([('value','=',value)])
        if srch:
            return srch[0].name
        return ""
    
    @api.model
    def get_by_value(self,str_date):
        if not str_date:
            return False
        dtDate=dtObj.parse(str_date)
        def dict_months(self):
            self._cr.execute("""SELECT VALUE,ID FROM CALENDAR_MONTH ORDER BY VALUE ASC""")
            result_list=self._cr.fetchall()
            return dict(result_list)
        months=dict_months(self)
        return months[dtDate.month]
    