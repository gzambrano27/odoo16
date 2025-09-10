# -*- coding: utf-8 -*-
# developed and maintained by RADORP Pvt.Ltd.

from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _find_no_asset_lot(self, move=False):
        """ *- argument move set to false :- expecting further customizations
            logic :-
                    -find received serial numbers from the purchase move
                    -find existing serial numbers with no asset linked
                    -loop received serial number on existing and return the first find.
            :return: received serial number with no asset linked.
        """
        if not self.tracking == 'serial':
            return False
        move_lots = move.purchase_line_id.move_ids.filtered(lambda x: x.state == 'done').lot_ids
        lot_with_asset = self.env['stock.lot'].search([('product_id', '=', self.id)])
        lot_exists=self.env['stock.lot']
        for lot in move_lots:
            if lot.id not in lot_with_asset.linked_asset_entries.linked_serial_id.ids:
                return lot
            else:
                lot_exists+=lot
        return lot_exists
