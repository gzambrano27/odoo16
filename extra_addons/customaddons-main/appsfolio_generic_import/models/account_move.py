# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of appsfolio. (Website: www.appsfolio.in).                            #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    custom_name = fields.Char(string='Custom Name')
    custom_sequence = fields.Boolean(string='Custom Sequence')
    system_sequence = fields.Boolean(string='System Sequence')
    invoice_name = fields.Char(string='Invoice Name')
    import_data = fields.Boolean(string="Import Data",default=False)
