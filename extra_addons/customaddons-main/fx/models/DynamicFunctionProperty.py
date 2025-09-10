# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, _

class DynamicFunctionProperty(models.Model):    
    _name="dynamic.function.property"
    _description="Propiedad de Función"
    
    name=fields.Char("Descripción",required=True,size=255)
    active=fields.Boolean("Activo",default=True)
    
    _order="name asc"
    
    _sql_constraints = [("dynamic_function_prop_name_unique_name","unique(name)","Descripción debe ser única"),
                        ]
    
