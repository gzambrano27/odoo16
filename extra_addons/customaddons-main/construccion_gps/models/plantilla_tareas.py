# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError
from odoo.osv.expression import AND, OR
from odoo.tools import float_round
from odoo.addons import decimal_precision as dp
from collections import defaultdict
import logging
from datetime import timedelta
_logger = logging.getLogger(__name__)


class TareasPlantilla(models.Model):
    """ Define las tareas correspondientes a las Plantillas """
    _name = 'plantilla.tareas'
    _description = 'Plantillas preestablecidas con Tareas'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']


    name = fields.Char('Nombre de la Plantilla', required=True, translate=True)
    company_id = fields.Many2one('res.company', 'Compañía', index=True, default=lambda self: self.env.company)
    line_ids = fields.One2many('plantilla.tareas.line', 'plantilla_tarea_id', 'Tareas Lines', copy=True) 

class TareasPlantillaLine(models.Model):
    _name = 'plantilla.tareas.line'
    _description = 'Detalle de Plantillas con Tareas'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    plantilla_tarea_id = fields.Many2one('plantilla.tareas', 'Parent Plantilla', index=True, ondelete='cascade', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char('Sección', required=True, store=True)
    duracion_total = fields.Integer(string='Duración Total (días)', compute='_compute_duracion_total', store=True, help="Suma de las duraciones de todas las tareas detalladas")
    detalle_ids = fields.One2many('plantilla.tareas.line.detalle', 'line_id', string='Detalles de la Tarea')

    @api.depends('detalle_ids.fecha_inicio', 'detalle_ids.fecha_fin')
    def _compute_duracion_total(self):
        for record in self:
            fechas_inicio = record.detalle_ids.mapped('fecha_inicio')
            fechas_fin = record.detalle_ids.mapped('fecha_fin')

            # Filtrar fechas válidas
            fechas_inicio = [f for f in fechas_inicio if f]
            fechas_fin = [f for f in fechas_fin if f]

            if fechas_inicio and fechas_fin:
                fecha_inicio_min = min(fechas_inicio)
                fecha_fin_max = max(fechas_fin)
                delta = (fecha_fin_max - fecha_inicio_min).days + 1
                record.duracion_total = max(delta, 1)
            else:
                record.duracion_total = 0


class TareasPlantillaLineDetalle(models.Model):
    _name = 'plantilla.tareas.line.detalle'
    _description = 'Detalle adicional de Tareas por Línea de Plantilla'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'fecha_inicio'

    line_id = fields.Many2one('plantilla.tareas.line', string='Línea de Plantilla', required=True, ondelete='cascade', index=True)
    tareas = fields.Char(string='Tareas', required=True, tracking=True)
    duracion = fields.Integer(string="Duración (días)", compute="_compute_duracion", store=True, help="Cantidad de días entre la fecha de comienzo y fin")
    fecha_inicio = fields.Date(string='Fecha de Comienzo', tracking=True)
    fecha_fin = fields.Date(string='Fecha Fin', tracking=True)
    cantidad = fields.Float(string='Cantidad', digits='Product Unit of Measure', tracking=True)
    costo = fields.Float(string='Costo', digits='Product Price', tracking=True)

    @api.depends('fecha_inicio', 'fecha_fin')
    def _compute_duracion(self):
        for record in self:
            if record.fecha_inicio and record.fecha_fin and record.fecha_fin >= record.fecha_inicio:
                fecha_actual = record.fecha_inicio
                dias_laborales = 0
                while fecha_actual <= record.fecha_fin:
                    if fecha_actual.weekday() < 5:
                        dias_laborales += 1
                    fecha_actual += timedelta(days=1)
                record.duracion = dias_laborales
            else:
                record.duracion = 0