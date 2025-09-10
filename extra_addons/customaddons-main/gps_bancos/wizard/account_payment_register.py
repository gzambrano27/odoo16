from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime,date
from dateutil.relativedelta import relativedelta

from ...calendar_days.tools import DateManager,CalendarManager
from ...message_dialog.tools import FileManager
dtObj=DateManager()
calendarO=CalendarManager()
fileO=FileManager()
from datetime import datetime, timedelta
from odoo import SUPERUSER_ID



class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    ref2 = fields.Char(
        string="Referencia 2",
    )

    def _create_payment_vals_from_wizard(self, batch_result):
        res = super()._create_payment_vals_from_wizard(batch_result)
        for rec in self:
            if rec.ref2:
                res.update({"ref2": rec.ref2})
        return res