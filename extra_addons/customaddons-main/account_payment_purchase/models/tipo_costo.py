# Copyright 2014 Akretion - Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2014 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, tools, _


class TipoCosto(models.Model):
    _name = "tipo.costo"
    
    code = fields.Char(string='Codigo')
    name = fields.Char(string='Descripcion')
    estado = fields.Selection([
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo')
        ], 'Estado', default='activo')