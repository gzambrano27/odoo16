# -*- coding: utf-8 -*-
# developed and maintained by RADORP Pvt.Ltd.

from odoo import fields, models


class AccountAssetCategory(models.Model):
    _inherit = 'account.asset.category'

    based_on_qty = fields.Boolean("Based on Quantity", default=False,
                                  help="If true, asset will be created based on the quantity purchased and link "
                                       "it with product and respective lot number")


class AccountAssetAsset(models.Model):
    _inherit = 'account.asset.asset'

    linked_product_id = fields.Many2one('product.product', 'Product', check_company=True, tracking=True,
                                        readonly=True, states={'draft': [('readonly', False)]},
                                        domain="[('type', '=', 'product'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    linked_serial_id = fields.Many2one('stock.lot', 'Serial No', tracking=True,
                                       domain="[('product_id', '=', linked_product_id), ('company_id', '=', company_id)]",
                                       check_company=True,
                                       readonly=True, states={'draft': [('readonly', False)]}, )
    purchase_order_id = fields.Many2one('purchase.order', 'Purchase order', tracking=True,
                                        readonly=True, states={'draft': [('readonly', False)]}, )
