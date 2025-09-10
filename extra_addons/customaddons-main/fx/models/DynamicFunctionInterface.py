# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, _

class DynamicFunctionInterface(models.Model):    
    _name="dynamic.function.interface"
    _description="Interfaz de Función"
    
    code=fields.Char("Código",required=True,size=32)
    name=fields.Char("Nombre",required=True,size=255)
    active=fields.Boolean("Activo",default=True)
    
    _order="name asc"
    
    _sql_constraints = [("dynamic_function_interface_name_unique_name","unique(name)","Descripción debe ser única"),
                        ("dynamic_function_interface_name_unique_value","unique(code)","Valor debe ser único"),
                        ]
    
