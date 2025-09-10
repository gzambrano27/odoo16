# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models,api

class CalendarDay(models.Model):    
    _name="calendar.day"
    _description="Días de la Semana"
    
    value=fields.Integer("Valor",required=True)
    name=fields.Char("Descripción",required=True)
    
    _order="value asc"
    
    @api.model
    def get_day_name(self,value):
        srch=self.search([('value','=',value)])
        if srch:
            return srch[0].name
        return ""
    
    _sql_constraints = [("calendar_day_name_unique_name","unique(name)","Descripción debe ser única"),
                        ("calendar_day_name_unique_value","unique(value)","Valor debe ser único"),
                        ]
