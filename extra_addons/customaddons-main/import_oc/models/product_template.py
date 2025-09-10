from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    imported_product = fields.Boolean(string="Imported Product", default=False)