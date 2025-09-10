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

class ClaseImportacion(models.Model):
    _name = "clase.importacion"
    
    secuencial = fields.Char('Secuencial',readonly='1')
    codigo = fields.Char('Codigo')
    name = fields.Char('Nombre')
    state = fields.Selection([
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo')], 'Estado', default='Activo')
    documento_transporte = fields.Char('Nombre')
    proveedor_id = fields.Many2one(
            'res.partner', 
            string="Proveedor",
            domain="[('supplier_rank', '>', 0), ('l10n_latam_identification_type_id.name', 'ilike', 'xtranjera')]"
        )
    _sql_constraints = [
        ('registro_class_uniq', 'unique(codigo,name)', 'Registro de Clase debe ser unico!!'),
    ]
    
    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('IMPORT')     
        vals['secuencial'] = sequence
        vals['codigo'] = sequence
        result = super(ClaseImportacion, self).create(vals)       
        return result
    
    @api.onchange('documento_transporte', 'proveedor_id')
    def _onchange_name(self):
        if self.documento_transporte and self.proveedor_id:
            self.name = f"{self.documento_transporte} - {self.proveedor_id.name}"
        else:
            self.name = False  # Deja el campo vacío si falta algún dato
