# Copyright 2014 Akretion - Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2014 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class FleetVehicleMulta(models.Model):
    _name = 'fleet.vehicle.multa'
    _description = 'Multas del Vehículo'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehículo')
    date = fields.Date(string='Fecha', required=True)
    amount = fields.Float(string='Monto', required=True)
    description = fields.Text(string='Descripción')
    responsable_id = fields.Many2one('res.partner')
    
class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    multa_ids = fields.One2many('fleet.vehicle.multa', 'vehicle_id', string='Multas')
    tipo = fields.Selection([
        ('propio', 'Propio'),
        ('rentado', 'Rentado'),
        ], 'Tipo', track_visibility='onchange', copy=False, default='propio')
    

class FleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'
    

    vehicle_type = fields.Selection(selection_add=[
        ('moto', 'Moto'),
        ('camion', 'Camion'),
        ('camioneta', 'Camioneta'),
        ('tractor', 'Tractor'),
    ], ondelete={
        'moto': 'set default',
        'camion': 'set default',
        'camioneta': 'set default',
        'tractor': 'set default',
    })