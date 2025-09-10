from odoo import fields, models, api


class MaterialPurchaseRequisition(models.Model):
    _inherit = "material.purchase.requisition"

    mrp_production_id = fields.Many2one("mrp.production", string="Manufacturing Order")