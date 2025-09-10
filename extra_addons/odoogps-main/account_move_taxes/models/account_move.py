# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from json import dumps

from odoo import _, api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    tax_line_ids = fields.One2many(
        comodel_name="account.move.taxes", inverse_name="move_id", string=_("Taxes")
    )

    @api.model
    def _get_tax_vals(self, line):
        tax_vals = {}
        if not line.tax_ids:
            return tax_vals
        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
        taxes = line.tax_ids.compute_all(
            price,
            line.move_id.currency_id,
            line.quantity,
            product=line.product_id,
        )["taxes"]
        base_tax = line.tax_ids.filtered(lambda x: x.include_base_amount)
        base = 0
        if base_tax:
            base = sum([t.get("amount") for t in taxes if base_tax.id == t.get("id")])
        for tl in taxes:
            tax_id = tl.get("id")
            tax = line.tax_ids.filtered(lambda x: x.id == tax_id and x.is_base_affected)
            if tax and tl.get("amount") != 0:
                tl.update({"base": base})
            tax_vals.update(
                {
                    tax_id: {
                        "move_id": self.id,
                        "sequence": tl.get("sequence"),
                        "amount": tl.get("amount"),
                        "base": tl.get("base"),
                        "name": tl.get("name"),
                        "account_id": tl.get("account_id"),
                    }
                }
            )
        return tax_vals

    def button_update_move_taxes(self):
        self.ensure_one()
        values = {}
        for line in self.invoice_line_ids:
            taxes = self._get_tax_vals(line)
            for tax in taxes:
                if not tax in values:
                    values.update({tax: taxes[tax]})
                else:
                    values[tax]["base"] += taxes[tax]["base"]
                    values[tax]["amount"] += taxes[tax]["amount"]
        if values:
            if self.tax_line_ids:
                self.tax_line_ids.unlink()
            for tax, vals in values.items():
                self.env["account.move.taxes"].create(vals)
        return True

    def button_edit_taxes(self):
        module = __name__.split("addons.")[1].split(".")[0]
        action_name = "{}.action_account_move_edit_taxes".format(module)
        action = self.sudo().env.ref(action_name, False).read()[0]
        tax_line = []
        taxes = self.mapped("invoice_line_ids.tax_ids").filtered(lambda x: x.is_vat)
        domain = [("is_vat", "=", False)]
        if self.move_type in ["in_invoice", "in_refund"]:
            domain.extend([("type_tax_use", "=", "purchase")])
        else:
            domain.extend([("type_tax_use", "=", "sale")])

        tax_ids = self.env["account.tax"].search(domain)
        if taxes:
            for tax in taxes:
                tax_line.append(
                    (
                        0,
                        0,
                        {
                            "tax_id": tax.id,
                            "tax_domain": dumps([("id", "in", tax_ids.ids)]),
                        },
                    )
                )
        if tax_line:
            action["context"] = {
                "default_move_id": self.id,
                "default_line_ids": tax_line,
            }
        return action


class AccountMoveTaxes(models.Model):
    """Account Move Taxes"""

    _name = "account.move.taxes"
    _order = "move_id,sequence"
    _description = __doc__

    move_id = fields.Many2one(
        comodel_name="account.move", string="Invoice", ondelete="cascade"
    )
    sequence = fields.Integer(default=0)
    tax_id = fields.Many2one(comodel_name="account.tax", string="Tax")
    account_id = fields.Many2one(comodel_name="account.account", string="Account")
    name = fields.Char(string="Description")
    base = fields.Float(string="Base", digits="Product Price")
    amount = fields.Float(string="Amount", digits="Product Price")
