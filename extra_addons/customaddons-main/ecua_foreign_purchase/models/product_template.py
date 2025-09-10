from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError

class ProductProduct(models.Model):
    _inherit = 'product.template'

    from_trade = fields.Boolean('Can be imported?')

    purchase_tariff_id = fields.Many2one('purchase.tariff', 'Tariff Subheading')

    arancel_ids = fields.Many2many('type.arancel', related='purchase_tariff_id.arancel_ids')

    @api.constrains('from_trade', 'invoice_method')
    def _check_invoice_method(self):
        """
        Obliga a seleccionar 'On ordered quantities' si es importación.
        """
        for record in self:
            if record.from_trade and record.invoice_policy != 'order':
                print('a')
                # raise ValidationError(
                #     "Cuando el producto es de importación, la Politica de Facturación debe ser 'Cantidades Ordenadas'."
                # )