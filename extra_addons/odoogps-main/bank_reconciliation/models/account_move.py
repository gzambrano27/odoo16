from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _get_invoice_in_payment_state(self):
        """Hook to give the state when the invoice becomes fully paid. This is necessary because the users working
        with only invoicing don't want to see the 'in_payment' state. Then, this method will be overridden in the
        accountant module to enable the 'in_payment' state."""
        return "in_payment"

    def button_cancel(self):
        for row in self:
            rec_lines = row.mapped("line_ids").filtered(
                lambda x: x.reconciled and x.statement_id
            )
            if rec_lines:
                raise ValidationError(
                    _(
                        "You can not modify any record that is part of a bank statement, ref: \n{}".format(
                            "\n".join(map(str, rec_lines.mapped("statement_id.name")))
                        )
                    )
                )
        return super(AccountMove, self).button_cancel()

    def button_draft(self):
        for row in self:
            rec_lines = row.mapped("line_ids").filtered(
                lambda x: x.reconciled and x.statement_id
            )
            if rec_lines:
                raise ValidationError(
                    _(
                        "You can not modify any record that is part of a bank statement, ref: \n{}".format(
                            "\n".join(map(str, rec_lines.mapped("statement_id.name")))
                        )
                    )
                )
        return super(AccountMove, self).button_draft()


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def get_bank_reference(self):
        return self.payment_id and self.payment_id.get_bank_reference() or ""

    @api.depends("payment_id", "payment_id.bank_reference", "payment_id.check_number")
    def compute_bank_reference(self):
        for row in self:
            row.bank_reference = row.get_bank_reference()
        return True

    bank_reference = fields.Char(
        string="Bank Reference",
        compute="compute_bank_reference",
        store=True,
    )
