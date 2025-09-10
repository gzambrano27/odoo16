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


class StockBackorderConfirmation(models.TransientModel):
    _inherit = "stock.backorder.confirmation"

    @api.model
    def _get_default_date(self):
        if self._context.get('active_ids',False):
            return None
        picking = self.env["stock.picking"].sudo().browse(self._context["active_ids"])
        return picking and picking.force_date

    date = fields.Datetime(string="Fecha Recepción",readonly=False,store=True,default=_get_default_date)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # res["date"] = self.env.context.get("force_period_date", fields.Datetime.now())
        if "pick_ids" in res and res.get("pick_ids"):
            pick_ids = res["pick_ids"][0][2]
            picking = self.env["stock.picking"].browse(pick_ids)[0]
            if picking.force_date:
                res["date"] = picking.force_date
            else:
                res["date"] = self.env.context.get("force_period_date", fields.Datetime.now())
        return res