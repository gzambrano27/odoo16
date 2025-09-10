from odoo import models, fields, api
from datetime import datetime, date

class PurchaseOrderCopyWizard(models.TransientModel):
    _name = 'purchase.order.copy.wizard'
    _description = 'Wizard to Copy Purchase Orders'

    origin_host = fields.Char('Origin Host', required=True)
    origin_db = fields.Char('Origin Database', required=True)
    origin_user = fields.Char('Origin User', required=True)
    origin_password = fields.Char('Origin Password', required=True)
    destination_host = fields.Char('Destination Host', required=True)
    destination_db = fields.Char('Destination Database', required=True)
    destination_user = fields.Char('Destination User', required=True)
    destination_password = fields.Char('Destination Password', required=True)
    objeto = fields.Selection([
        ('mrp.production', 'Produccion'),
        ('purchase.order', 'Orden de Compra'),
        ('account.move', 'Factura de Proveedor')
    ], 'Objeto', copy=False, default='purchase.order')
    fecha_desde = fields.Datetime('Fecha Desde')
    fecha_hasta = fields.Datetime('Fecha Hasta')

    def copy_orders(self):
        self.ensure_one()
        order_copy_model = self.env['purchase.order.copy']
        copied_count = order_copy_model.copy_purchase_orders(
            self.origin_host, self.origin_db, self.origin_user, self.origin_password,
            self.destination_host, self.destination_db, self.destination_user, self.destination_password, self.objeto, self.fecha_desde, self.fecha_hasta
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'{copied_count} purchase orders copied successfully.',
                'type': 'success',
                'sticky': False,
            }
        }