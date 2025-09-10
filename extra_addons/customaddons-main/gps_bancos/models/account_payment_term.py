# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    validate_with_base_amount=fields.Boolean(string="Calcular con Base Imponible",default=True)