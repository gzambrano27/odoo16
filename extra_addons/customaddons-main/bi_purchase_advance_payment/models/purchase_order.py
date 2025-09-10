# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    account_payment_ids = fields.One2many('account.payment', 'purchase_id', string="Pay purchase advanced",
                                          readonly=True)
    amount_residual = fields.Float('Residual', compute='_compute_residual', store= True)
    val_pagado = fields.Float('Valor Pagado')

    @api.depends('amount_total','val_pagado')
    def _compute_residual(self):
        for x in self:
            x.amount_residual = x.amount_total - x.val_pagado
