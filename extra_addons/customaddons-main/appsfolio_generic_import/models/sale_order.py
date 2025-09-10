# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of appsfolio. (Website: www.appsfolio.in).                            #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    import_data = fields.Boolean(
        string="Import data",
        default=False
    )
    custom_sequence = fields.Boolean(string='Custom Sequence')
    system_sequence = fields.Boolean(string='System Sequence')
    sale_name = fields.Char(string='Sale Name')
