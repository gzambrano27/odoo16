# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools, api
from odoo.exceptions import ValidationError
from odoo.tools import formatLang


class StockPicking(models.Model):
    _inherit = "stock.picking"

    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        domain="[('purchase_order_type', '=', 'service'), ('state', '=', 'purchase'), ('partner_id', '=', partner_id)]"
    )


    @api.onchange('purchase_order_id')
    def _onchange_purchase_order_id(self):
        if self.purchase_order_id:
            self.analytic_distribution = self.purchase_order_id.analytic_distribution
        else:
            self.analytic_distribution = {}


    @api.constrains('purchase_order_id', 'analytic_distribution')
    def _check_analytic_account_match(self):
        for record in self:
            po = record.purchase_order_id
            #if po and record.analytic_distribution and po.analytic_distribution != record.analytic_distribution:
            if po and record.analytic_distribution != False:
                if po.analytic_distribution != record.analytic_distribution:
                    raise ValidationError("La cuenta analítica de la orden de compra no coincide con la del registro actual.")
            if po and not record.analytic_distribution:
                raise ValidationError("La cuenta analítica de la orden de compra no coincide con la del registro actual.")







