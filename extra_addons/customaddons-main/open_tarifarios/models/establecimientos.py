# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class Establecimientos(models.Model):
    _name = "establecimientos"
    _description = 'Registro Maestro de establecimientos'
    
    codigo = fields.Char("Codigo", size=5)
    name = fields.Text("Establecimiento")
    state = fields.Selection([('ACTIVO','ACTIVO'),('INACTIVO','INACTIVO')],    'Estado', default='ACTIVO')
              