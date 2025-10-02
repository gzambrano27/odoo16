# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models,api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    for_local_payment = fields.Boolean(string='Para pagos Locales',default=False)
    for_exterior_payment = fields.Boolean(string='Para pagos Exterior', default=False)

    for_check = fields.Boolean(string='Para Cheques', default=False)
    for_bank = fields.Boolean(string='Para Bancos', default=False)
    for_tc = fields.Boolean(string='Para Tarjeta de Credito', default=False)

    @api.onchange('type')
    def onchange_journal_type(self):
        if not self.type in ('bank','cash'):
            self.for_local_payment = False
            self.for_exterior_payment = False
            self.for_check = False
            self.for_bank = False
            self.for_tc = False
