# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, _, api, fields, models


class AccountMoveEditTaxes(models.TransientModel):
    """Account Move edit taxes"""

    _name = "account.move.edit.taxes"
    _description = __doc__

    move_id = fields.Many2one("account.move", required=True, string="move")
    option = fields.Selection(
        selection=[("add", "Add"), ("remove", "Remove")], string="Option", default="add"
    )
    tax_id = fields.Many2one("account.tax", string=_("Tax"))
    line_ids = fields.One2many(
        comodel_name="account.move.add.tax",
        inverse_name="helper_id",
        string=_("Tax Details"),
    )

    @api.onchange("move_id", "option")
    def onchange_move_id(self):
        taxes = (
            self.env["account.tax"].search([])
            if self.option == "add"
            else self.move_id.mapped("invoice_line_ids.tax_ids")
        )
        return {
            "domain": {
                "tax_id": [
                    ("id", "in", taxes.ids),
                    ("company_id", "=", self.move_id.company_id.id),
                ]
            }
        }

    def add_tax(self):
        for line in self.line_ids:
            if line.tax_ids:
                self.update_tax(line.tax_id, line.tax_ids)
        self.move_id.button_update_move_taxes()
        return True

    def update_tax(self, tax_id, new_taxes):
        """Add the given taxes to all the invoice line of the current invoice"""
        move_id = self.move_id.with_context(check_move_validity=False)
        for tax in new_taxes:
            move_id.invoice_line_ids.filtered(lambda x: tax_id in x.tax_ids).write(
                {"tax_ids": [(4, tax.id)]}
            )
        container = {"records": move_id}
        move_id._check_balanced(container)
        move_id._sync_dynamic_lines(container)

    def remove_tax(self):
        """Remove the given taxes to all the invoice line of the current invoice"""
        move_id = self.move_id.with_context(check_move_validity=False)
        move_id.invoice_line_ids.with_context(dynamic_unlink=True).write(
            {"tax_ids": [(3, self.tax_id.id)]}
        )
        container = {"records": move_id}
        move_id._check_balanced(container)
        move_id._sync_dynamic_lines(container)
        self.move_id.button_update_move_taxes()


class AccountMoveAddTax(models.TransientModel):
    """Account Move Tax Detail"""

    _name = "account.move.add.tax"
    _description = __doc__

    helper_id = fields.Many2one(
        comodel_name="account.move.edit.taxes", string=_("Helper")
    )
    tax_id = fields.Many2one(comodel_name="account.tax", required=True)
    tax_domain = fields.Char()
    tax_ids = fields.Many2many(comodel_name="account.tax", required=True)
