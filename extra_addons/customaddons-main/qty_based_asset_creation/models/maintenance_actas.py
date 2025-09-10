from venv import create

from odoo import models, fields, api

class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    linked_product_id = fields.Many2one('product.product', 'Product', check_company=True, tracking=True,
                                        readonly=False,
                                        domain="[('type', '=', 'product'), '|', ('company_id', '=', False), ('company_id', '=', company_id), ('active', '=', True)]")

    linked_serial_id = fields.Many2one('stock.lot', 'Serial Interno No', tracking=True,
                                       domain="[('product_id', '=', linked_product_id), ('company_id', '=', company_id)]",
                                       check_company=True,
                                       readonly=False )
    _sql_constraints = [
        ('serial_equipo', 'UNIQUE(linked_serial_id, linked_product_id)', 'Solo puede existir un equipo por serial interno!')
    ]
