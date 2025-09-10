# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of appsfolio. (Website: www.appsfolio.in).                            #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

from odoo import fields, models, api


class GenInventory(models.Model):
    _name = "gen.inventory"

    product_counter = fields.Integer(string="Counter")

    @api.model
    def default_get(self, fields):
        record = super(GenInventory, self).default_get(fields)
        product_id = self.env['gen.inventory'].sudo().search([], order="id desc", limit=1)
        if product_id:
            record.update({
                'product_counter': product_id.product_counter,
            })
        else:
            record.update({
                'product_counter': '',
            })
        return record
        