# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
from ...message_dialog.tools import FileManager
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager

fileO = FileManager()
dateO = DateManager()
calendarO = CalendarManager()
from datetime import datetime, timedelta
import pytz


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    request_type_id=fields.Many2one('account.payment.request.type','Tipo de Solicitud')



