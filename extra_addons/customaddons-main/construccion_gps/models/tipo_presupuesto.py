# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _, Command
from datetime import datetime, timedelta

class TipoPresupuesto(models.Model):
    _name = 'tipo.presupuesto'
    _description = 'Tipo Presupuesto'
    _inherit = ['mail.thread']
    _order = 'codigo asc'
    _rec_name = 'codigo'

    name = fields.Char(string='Nombre', required=True)
    codigo = fields.Char(string='Código', required=True)
    state = fields.Selection([
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo')], 'Estado', default='Activo')

    _sql_constraints = [
        ('tipo_psp_uniq', 'unique(codigo,name)', 'Tipo de Presupuesto debe ser único!!')
    ]