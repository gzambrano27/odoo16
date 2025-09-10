from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    old_code = fields.Char(string='Old code')

    @api.constrains("old_code")
    def _check_uniq_old_code(self):
        for rec in self:
            if rec.old_code:
                product = self.env['product.template'].search([
                    ('old_code', '=', rec.old_code),
                    ('active', '=', True),
                    ('company_id', '=', rec.company_id.id),
                    ('id', '!=', rec.id)
                ])
                if len(product) > 1:
                    raise UserError(_("El código debe ser único"))
