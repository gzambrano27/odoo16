from odoo import models, fields

class MaintenancePackage(models.Model):
    _name = 'maintenance.package'
    _description = 'Paquete de Mantenimiento'

    name = fields.Char(string="Nombre del Paquete de Mantenimiento", required=True)
    maintenance_type = fields.Selection(
        selection=[
            ('preventivo', 'Preventivo'),
            ('correctivo', 'Correctivo'),
        ],
        string="Tipo de Mantenimiento",
        required=True
    )
    service_ids = fields.One2many('maintenance.service', 'package_id', string="Servicios de Mantenimiento")
