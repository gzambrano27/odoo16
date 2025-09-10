# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of appsfolio. (Website: www.appsfolio.in).                            #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    import_data = fields.Boolean(string="Import data", default=False)
