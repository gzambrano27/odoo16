# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SelecRequestAcceptanceWizard(models.TransientModel):
    _name = "select.request.acceptance.wizard"
    _description = "Select Request Acceptance Wizard"

    require_pr = fields.Boolean(default=lambda self: self._get_require_pr())
    pr_id = fields.Many2one(
        comodel_name="request.acceptance",
        string="Request Acceptance",
        domain="[('id', 'in', pr_ids)]",
    )
    pr_ids = fields.Many2many(
        comodel_name="request.acceptance",
        compute="_compute_pr_ids",
    )
    name_rs = fields.Char(related="pr_id.name_rs", string="Requisicion", readonly=True)

    def _get_require_pr(self):
        return True
        # return self.env.user.has_group(
        #     "purchase_work_acceptance.group_enforce_wa_on_invoice"
        # )

    @api.depends("require_pr")
    def _compute_pr_ids(self):
        self.ensure_one()
        self.pr_ids = self.env["request.acceptance"]._get_valid_pr(
            "invoice", self.env.context.get("active_id")
        )

    def _get_purchase_order_with_context(self, order_id):
        return (
            self.env["macro.purchase.request"]
            .browse(order_id)
            .with_context(create_bill=False, pr_id=self.pr_id.id)
        )

    def button_create_vendor_bill(self):
        self.ensure_one()
        order_id = self._context.get("active_id")
        order = self._get_purchase_order_with_context(order_id)
        return order.sudo().action_create_invoice()
