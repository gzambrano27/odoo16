from odoo import models, fields, api
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        for picking in self:
            # Verificar si el picking es de tipo salida (outgoing)
            if picking.picking_type_id.code == 'outgoing':
                purchase_orders = picking.move_lines.mapped('purchase_line_id.order_id')

                # Filtrar órdenes de compra que sean de importación
                import_purchase_orders = purchase_orders.filtered(lambda po: po.importacion)

                # Buscar órdenes de importación no completadas
                incomplete_import_orders = self.env['purchase.order'].search([
                    ('id', 'in', import_purchase_orders.ids),
                    ('state_confirmed', '!=', True)
                ])

                if incomplete_import_orders:
                    raise ValidationError(
                        "No se puede validar el despacho porque existe una orden de importación sin completar."
                    )

        return super(StockPicking, self).button_validate()
