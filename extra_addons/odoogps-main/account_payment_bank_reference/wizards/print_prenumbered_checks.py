from odoo import api, fields, models


class PrintPreNumberedChecks(models.TransientModel):
    _inherit = "print.prenumbered.checks"

    def print_checks(self):
        res = super(PrintPreNumberedChecks, self).print_checks()
        payments = self.env["account.payment"].browse(self.env.context["payment_ids"])
        for payment in payments:
            payment.set_bank_reference()
        return res
