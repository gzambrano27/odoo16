from odoo import models, fields

class MaintenanceService(models.Model):
    _name = 'maintenance.service'
    _description = 'Servicio de Mantenimiento'

    name = fields.Char(string="Nombre del Servicio de Mantenimiento", required=True)
    package_id = fields.Many2one('maintenance.package', string="Paquete de Mantenimiento", required=True)
    description = fields.Text(string="Descripción del Servicio")
