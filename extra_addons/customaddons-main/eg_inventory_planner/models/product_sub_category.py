from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductSubCategory(models.Model):
    _name = "product.sub.category"
    _description = "Product Sub Category"
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'

    name = fields.Char('Name', index=True, required=True)
    complete_name = fields.Char(
        'Complete Name', compute='_compute_complete_name', recursive=True,
        store=True)
    parent_id = fields.Many2one('product.sub.category', 'Parent Category', index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    child_id = fields.One2many('product.sub.category', 'parent_id', 'Child Categories')
    product_count = fields.Integer(
        '# Products', compute='_compute_product_count',
        help="The number of products under this category (Does not consider the children categories)")

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name

    def _compute_product_count(self):
        self.product_count = self.env['product.template'].search_count([('sub_categ_ids', 'child_of', self.ids)])

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive categories.'))
        return True

    @api.model
    def name_create(self, name):
        return self.create({'name': name}).name_get()[0]
