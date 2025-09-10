from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    apu_ids = fields.One2many('apu.apu', 'product_tmpl_id', string="Lista de APU")
    apu_count = fields.Integer(string="Cantidad de APU", compute="_compute_apu_count")

    def action_view_apu(self):
        return {
            'name': 'Lista de APU',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'apu.apu',
            'domain': [('product_tmpl_id', '=', self.id)],
            'context': {'default_product_tmpl_id': self.id},
        }

    @api.depends('apu_ids')
    def _compute_apu_count(self):
        for product in self:
            product.apu_count = len(product.apu_ids)
