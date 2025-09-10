# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

#
# Please note that these reports are not multi-currency !!!
#

import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv.expression import AND, expression


class PurchaseOrder(models.Model):

    _inherit = 'purchase.order'

    def agrupar(self):
        self.ensure_one()
        v = {}
        for brw_line in self.order_line:
            if brw_line.product_id not in v:
                v[brw_line.product_id] = 0.00
            v[brw_line.product_id] += brw_line.product_qty
        print(v)
        print(v.values())
        return v