from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from ...calendar_days.tools import CalendarManager,DateManager,MonthManager
dtObj = DateManager()

class ResourceCalendar(models.Model):
    _inherit="resource.calendar"

    default=fields.Boolean("Por defecto",default=True)