# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_enable_pr_on_mpr = fields.Boolean(
        string="Enable PR on Macro Purchase Request",
        implied_group="purchase_request_acceptance.group_enable_pr_on_mpr",
    )
    