from odoo import models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    _description = 'Autofill qty done on production order'

    def autofill_qty_done(self):
        for line in self.move_raw_ids:
            line.quantity_done = line.product_uom_qty


