from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"

    @api.constrains('hour_from', 'hour_to')
    def _check_hours(self):
        for resource in self:
            if not (0 <= resource.hour_from <= 23.98):
                raise ValidationError(_('The hour_from entered is incorrect, please check'))
            if not (0 <= resource.hour_to <= 23.98):
                raise ValidationError(_('The hour_to entered is incorrect, please check'))

