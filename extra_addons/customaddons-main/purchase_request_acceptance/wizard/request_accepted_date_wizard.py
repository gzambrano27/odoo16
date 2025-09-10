# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SelectRequestAcceptanceWizard(models.TransientModel):
    _name = "request.accepted.date.wizard"
    _description = "Select request accepted date"

    date_accept = fields.Datetime(
        string="Accepted Date",
        required=True,
        default=fields.Datetime.now,
        readonly=True
    )

    def button_accept(self):
        active_id = self.env.context.get("active_id")
        request_acceptance = self.env["request.acceptance"].browse(active_id)
        request_acceptance.with_context(manual_date_accept=False).button_accept(
            force=self.date_accept
        )
