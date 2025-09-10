# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models,api

class CalendarHoliday(models.Model):    
    _name="calendar.holiday"
    _description="Días Festivos"
    
    name=fields.Char("Nombre",required=True)
    active=fields.Boolean("Activo",default=True)
    
    _sql_constraints = [("calendar_name_unique_code","unique(name)","Nombre debe ser único"),
                        ]
    
    _order="name asc"
    
