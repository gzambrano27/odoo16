# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class hrSectores(models.Model):
    _name = "hr.sectores"
    _description = 'Registro Maestro de sectores'
    
    codigo = fields.Char("Codigo", size=3)
    name = fields.Char("Sector", size=1024)
    state = fields.Selection([('ACTIVO','ACTIVO'),('INACTIVO','INACTIVO')],    'Estado', default='ACTIVO')