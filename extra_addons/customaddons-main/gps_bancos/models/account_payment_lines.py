# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api
from odoo.exceptions import ValidationError

class AccountPaymentLines(models.Model):
    _inherit = "account.payment.lines"

    reconciliation_line_id=fields.Many2one('document.bank.reconciliation.line','Reconciliacion')

    def update_copy_values(self, copy_values_lines):
        self.ensure_one()
        copy_values_lines['reconciliation_line_id']=self.reconciliation_line_id and self.reconciliation_line_id.id or False
        return copy_values_lines