from odoo import models, fields, api
from odoo.tools import format_date


class ProductPurchaseHistory(models.Model):
    _name = 'product.purchase.history'
    _description = "Product Purchase History"

    name = fields.Char(string="Name")
    inventory_plan_id = fields.Many2one(comodel_name="inv.plan", string="Purchase History")
    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    total_purchase_order = fields.Integer(string="Total Purchase Order")
    average_daily_purchase = fields.Float(string="Average Daily Purchase")
    maximum_daily_purchase_qty = fields.Float(string="Maximum Daily Purchase Qty")
    duration_in_day = fields.Integer(string="Duration In Day")
    product_id = fields.Many2one(comodel_name="product.product", string="Product")
    quantity = fields.Float(string="Quantity")
