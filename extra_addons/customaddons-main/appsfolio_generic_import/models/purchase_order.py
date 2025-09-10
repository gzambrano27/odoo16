# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of appsfolio. (Website: www.appsfolio.in).                            #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    custom_sequence = fields.Boolean(string='Custom Sequence')
    system_sequence = fields.Boolean(string='System Sequence')
    purchase_name = fields.Char(string='Purchase Name')
    import_data = fields.Boolean(
        string="Import data",
        default=False
    )
