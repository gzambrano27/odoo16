from odoo import models, fields, api
from odoo.tools import format_date


class ProductSaleHistory(models.Model):
    _name = 'product.sale.history'
    _description = "Product Sale History"

    name = fields.Char(string="Name")
    inventory_plan_id = fields.Many2one(comodel_name="inv.plan", string="Sale History")
    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    total_sale_order = fields.Integer(string="Total Sale Order")
    average_daily_sale = fields.Float(string="Average Daily Sale")
    maximum_daily_sale_qty = fields.Float(string="Maximum Daily Sale Qty")
    duration_in_day = fields.Integer(string="Duration In Day")
    product_id = fields.Many2one(comodel_name="product.product", string="Product")
    quantity = fields.Float(string="Quantity")
