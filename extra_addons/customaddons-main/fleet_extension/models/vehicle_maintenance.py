from odoo import models, fields, api

class VehicleMaintenance(models.Model):
    _name = 'vehicle.maintenance'
    _description = 'Mantenimiento del Vehículo'

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string="Vehículo",
        required=True,
        ondelete="cascade"
    )
    maintenance_type = fields.Selection(
        selection=[
            ('preventivo', 'Preventivo'),
            ('correctivo', 'Correctivo'),
            ('lavada', 'Lavada'),
            ('instalacion', 'Instalación'),
            ('respuesto', 'Respuesto')
        ],
        string="Tipo de Mantenimiento",
        required=True
    )
    package_id = fields.Many2one('maintenance.package', string="Paquete de Mantenimiento")
    service_id = fields.Many2one('maintenance.service', string="Servicio de Mantenimiento")

    @api.onchange('maintenance_type')
    def _onchange_maintenance_type(self):
        """Actualizar paquetes según el tipo de mantenimiento seleccionado."""
        if self.maintenance_type:
            return {'domain': {'package_id': [('maintenance_type', '=', self.maintenance_type)]}}
        else:
            self.package_id = False
            self.service_id = False
            return {'domain': {'package_id': []}}

    @api.onchange('package_id')
    def _onchange_package_id(self):
        """Actualizar servicios según el paquete de mantenimiento seleccionado."""
        if self.package_id:
            return {'domain': {'service_id': [('package_id', '=', self.package_id.id)]}}
        else:
            self.service_id = False
            return {'domain': {'service_id': []}}
