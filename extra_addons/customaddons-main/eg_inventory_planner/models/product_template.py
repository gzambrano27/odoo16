from datetime import datetime

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    sub_categ_ids = fields.Many2many("product.sub.category", string="Sub Category")
    last_published_date = fields.Datetime("Last Published Date")

    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        if vals.get("website_published"):
            self.last_published_date = datetime.now()
        return res
