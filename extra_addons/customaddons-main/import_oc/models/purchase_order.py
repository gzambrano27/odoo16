from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    imported_oc = fields.Boolean(string="Imported OC", default=False)