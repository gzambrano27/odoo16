# custom_module/models/stock_picking.py
from odoo import models, api
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.constrains('move_ids_without_package')
    def _check_received_quantity(self):
        for picking in self:
            for move in picking.move_ids_without_package:
                purchase_line = move.purchase_line_id
                if purchase_line and move.quantity_done > purchase_line.product_qty:
                    raise ValidationError(
                        "La cantidad recibida (%s) no puede ser mayor que la cantidad pedida (%s) para el producto %s." % 
                        (move.quantity_done, purchase_line.product_qty, move.product_id.display_name)
                    )
                
    def action_cancel_picking(self):
        for picking in self.env['stock.picking'].search([('id','=',370)]):
            if picking.state not in ['cancel','done']:
                picking.action_cancel()
        return True
    
    def action_done(self):
        for picking in self:
            # Bloquear recepciones, salidas y transferencias
            if picking.date_done <='2024-12-31 23:59:59' and picking.company_id in(2,3):
                if picking.picking_type_id.code in ['incoming', 'outgoing', 'internal']:
                    raise ValidationError("No se pueden validar movimientos de recepción, salida o transferencia en este momento.")
        return super(StockPicking, self).action_done()