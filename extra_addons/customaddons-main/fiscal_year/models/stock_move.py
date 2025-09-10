# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tools import format_datetime
from odoo.http import request
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager

dateO = DateManager()
calendarO = CalendarManager()
import pytz

class StockMove(models.Model):
    _inherit = 'stock.move'

    def write(self, vals):
        for brw_each in self:
            if ("date" in vals) and ("date_deadline" in vals):
                if vals["date_deadline"]!=vals["date"]:
                    vals["date"]=vals["date_deadline"]
                print(vals)
        return super(StockMove , self).write(vals)



