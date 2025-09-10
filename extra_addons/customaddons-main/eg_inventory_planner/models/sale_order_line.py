from odoo import models, fields, api
from odoo.tools import format_date


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    sale_history_id = fields.Many2one(comodel_name='inv.plan', string="Sale History")
    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    total_sale_order = fields.Integer(string="Total Sale Order")
    average_daily_sale = fields.Float(string="Average Daily Sale")
    maximum_daily_sale_qty = fields.Float(string="Maximum Daily Sale Qty")
    duration_in_day = fields.Integer(string="Duration In Day")

    @api.depends('duration_in_day', 'total_sale_order')
    def _compute_average_daily_sale(self):
        self.average_daily_sale = 0
        self.average_daily_sale = self.total_sale_order / self.duration_in_day

