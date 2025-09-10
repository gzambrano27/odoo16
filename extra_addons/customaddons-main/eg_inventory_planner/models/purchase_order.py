from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    inv_plan_id = fields.Many2one('inv.plan', string="Report", readonly=True, tracking=True, ondelete='restrict')
