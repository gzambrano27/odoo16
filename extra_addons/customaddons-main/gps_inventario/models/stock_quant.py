# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from odoo.exceptions import ValidationError,UserError
from odoo import api, fields, models, _
from odoo.tools.view_validation import READONLY


class StockQuant(models.Model):
    _inherit = "stock.quant"

    warehouse_id = fields.Many2one('stock.warehouse', related='location_id.warehouse_id', store=True, readonly=True)
    product_name = fields.Char(string="Name Product", related="product_id.name", store=True, readonly=True)
    product_code = fields.Char(string="Code Product", related="product_id.default_code", store=True, readonly=True)
    value_float = fields.Float('Value (Float)', compute='_compute_value_float', store=True)

    def _get_inventory_move_values(self, qty, location_id, location_dest_id, out=False):
        res_move = super(StockQuant,self)._get_inventory_move_values(qty, location_id, location_dest_id, out=out)
        return res_move

    @api.depends('value')
    def _compute_value_float(self):
        for record in self:
            record.value_float = record.value if record.value else 0.0