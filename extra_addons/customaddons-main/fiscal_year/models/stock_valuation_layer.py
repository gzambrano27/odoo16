# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager

dateO = DateManager()
calendarO = CalendarManager()

from itertools import chain
from odoo.tools import groupby
from collections import defaultdict

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    def _validate_accounting_entries(self):
        am_vals = []
        aml_to_reconcile = defaultdict(set)
        for svl in self:
            if not svl.with_company(svl.company_id).product_id.valuation == 'real_time':
                continue
            if svl.currency_id.is_zero(svl.value):
                continue
            move = svl.stock_move_id
            if not move:
                move = svl.stock_valuation_layer_id.stock_move_id
            am_vals += move.with_company(svl.company_id)._account_entry_move(svl.quantity, svl.description, svl.id, svl.value)
        if am_vals:
            account_moves = self.env['account.move'].sudo().create(am_vals)
            account_moves=account_moves.with_context({"pass_account_move":True})
            account_moves._post()
        products_svl = groupby(self, lambda svl: svl.product_id)
        for product, svls in products_svl:
            svls = self.browse(svl.id for svl in svls)
            moves = svls.stock_move_id
            if svls.company_id.anglo_saxon_accounting:
                moves._get_related_invoices()._stock_account_anglo_saxon_reconcile_valuation(product=product)
            moves = (moves | moves.origin_returned_move_id).with_prefetch(chain(moves._prefetch_ids, moves.origin_returned_move_id._prefetch_ids))
            for aml in moves._get_all_related_aml():
                if aml.reconciled or aml.move_id.state != "posted" or not aml.account_id.reconcile:
                    continue
                aml_to_reconcile[(product, aml.account_id)].add(aml.id)
        for aml_ids in aml_to_reconcile.values():
            self.env['account.move.line'].browse(aml_ids).reconcile()

