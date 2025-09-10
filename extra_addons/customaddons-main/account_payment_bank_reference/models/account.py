import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    bank_reference = fields.Char(
        string="Bank Reference",
        copy=False,
    )

    def get_bank_reference(self):
        if not self.bank_reference or self.bank_reference == "0":
            return str(self.check_number) if self.check_number else ""
        else:
            return self.bank_reference or ""

    @api.onchange("check_number", "bank_reference")
    def _onchange_set_bank_bank_number(self):
        if not self.bank_reference and self.check_number:
            self.set_bank_reference()
        if self.bank_reference and re.compile(" ").search(self.bank_reference):
            self.bank_reference = " ".join(self.bank_reference.split())

    def set_bank_reference(self):
        for row in self:
            if not row.bank_reference or row.bank_reference == "0":
                row.bank_reference = row.get_bank_reference()
        return True

    def print_checks(self):
        res = super(AccountPayment, self).print_checks()
        self.set_bank_reference()
        return res

    def action_post(self):
        res = super(AccountPayment, self).action_post()
        self.set_bank_reference()
        return res

    @api.constrains("journal_id", "bank_reference")
    def _check_bank_reference(self):
        for row in self:
            if self.bank_reference:
                refs = self.search(
                    [
                        ("id", "!=", row.id),
                        ("journal_id", "=", row.journal_id.id),
                        ("bank_reference", "=", row.bank_reference),
                    ]
                )
                if refs:
                    raise ValidationError(
                        _(
                            "The Bank Reference has already been used and this must be unique per journal. \n {}".format(
                                ", ".join(map(str, refs.mapped("name")))
                            )
                        )
                    )


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    bank_reference = fields.Char(
        string="Bank Reference",
    )

    def _create_payment_vals_from_wizard(self, batch_result):
        res = super()._create_payment_vals_from_wizard(batch_result)
        for rec in self:
            if rec.bank_reference:
                res.update({"bank_reference": rec.bank_reference})
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def get_bank_reference(self):
        return self.payment_id and self.payment_id.get_bank_reference() or ""

    @api.depends("payment_id", "payment_id.bank_reference", "payment_id.check_number")
    def _compute_bank_reference(self):
        for row in self:
            row.bank_reference = row.get_bank_reference()
        return True

    bank_reference = fields.Char(
        string="Bank Reference",
        compute=_compute_bank_reference,
        store=True,
    )
