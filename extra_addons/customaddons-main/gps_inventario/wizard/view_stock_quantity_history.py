# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from xlrd import open_workbook
from odoo.exceptions import ValidationError
from ...calendar_days.tools import CalendarManager, DateManager
from ...message_dialog.tools import FileManager

dtObj = DateManager()
clObj = CalendarManager()
flObj = FileManager()


class StockQuantityHistory(models.TransientModel):
    _inherit = "stock.quantity.history"

    location_id = fields.Many2one("stock.location", "Ubicacion", required=False )

    def open_at_date(self):
        if not self.location_id:
            action=super(StockQuantityHistory,self).open_at_date()
            return action
        action = super(StockQuantityHistory, self).open_at_date()
        context=action.get("context",{})
        if self.location_id:
            context["location"]=self.location_id.id
        action["context"]=context
        return action