# -*- coding: utf-8 -*-
# © <2024> <Washington Guijarro>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import (
    api,
    models,
    fields,
    _
)
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError
from datetime import datetime, date, time, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_is_zero, float_compare

class CentroCostoTipoProyecto(models.Model):
    _name = "centro.costo.tipo.proyecto"
    
    codigo = fields.Char('Codigo')
    name = fields.Char('Nombre')
    state = fields.Selection([
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo')], 'Estado', default='Activo')
    _sql_constraints = [
        ('registro_cctipoproy_uniq', 'unique(codigo,name)', 'Registro de Tipo Proyecto de centro de costo debe ser unico!!'),
    ]
    