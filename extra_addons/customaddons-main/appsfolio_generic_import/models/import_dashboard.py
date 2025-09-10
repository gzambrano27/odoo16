# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of appsfolio. (Website: www.appsfolio.in).                            #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

from odoo import models, fields


class ImportDashboard(models.Model):
    _name = 'import.dashboard'
    _description = "import Dashboard"

    name = fields.Char(string='Import Dashboard')
    state = fields.Selection([
        ('sale.order', 'Sale Orders'),
        ('purchase.order', 'Purchase Orders'),
        ('account.move', 'Invoice/Bill'),
        ('product.template', 'Product Template'),
        ('product.product', 'Product Variant'),
        ('stock.picking', 'Picking'),
        ('mrp.bom', 'mrp'),
        ('res.partner', 'Partner'),
        ('product.pricelist', 'Price list'),
        ('stock.quant', 'Inventory'),
        ('account.payment', 'payment'),
        ('account.account', 'Import Chart of Account')],
        string="State"
    )
    pending_data = fields.Integer(
        string='Pending Data',
        default=0,
        compute="_count"
    )

    def _count(self):
        model_mapping = {
            'sale.order': self.env['sale.order'],
            'purchase.order': self.env['purchase.order'],
            'account.move': self.env['account.move'],
            'product.template': self.env['product.template'],
            'product.product': self.env['product.product'],
            'stock.picking': self.env['stock.picking'],
            'mrp.bom': self.env['mrp.bom'],
            'res.partner': self.env['res.partner'],
            'product.pricelist': self.env['product.pricelist'],
            'stock.quant': self.env['stock.quant'],
            'account.payment': self.env['account.payment'],
            'account.account': self.env['account.account']
        }
        for count in self:
            if count.state in model_mapping:
                import_count = model_mapping[count.state].sudo().search_count([
                    ('import_data', '=', True)
                ])
                count.pending_data = import_count
            else:
                count.pending_data = 0
        return True
