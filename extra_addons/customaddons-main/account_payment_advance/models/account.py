from json import dumps

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class AccountAccount(models.Model):
    _inherit = "account.account"

    prepayment_account = fields.Boolean(
        string="Is for Prepayments?",
        help="Check this box if this account will be used to record advance payments.",
    )

    @api.onchange("advances_account")
    def _onchange_advances_account(self):
        if self.prepayment_account:
            self.reconcile = True


class AccountMove(models.Model):
    _inherit = "account.move"

    has_prepayment = fields.Boolean(compute="_has_prepayment")
    prepayment_assignment = fields.Boolean()

    def _has_prepayment(self):
        for row in self:
            prepayment = False
            payment, payment_type = self._get_prepayment_lines()
            if (
                payment
                and row.move_type
                in [
                    "out_invoice",
                    "out_refund",
                    "in_invoice",
                    "in_refund",
                ]
                and row.payment_state not in ["paid", "reversed", "invoicing_legacy"]
            ):
                prepayment = True
            row.has_prepayment = prepayment
        return True

    def _get_prepayment_lines(self):
        domain = [
            ("account_id.prepayment_account", "=", True),
            ("account_id.reconcile", "=", True),
            (
                "partner_id",
                "=",
                self.env["res.partner"]._find_accounting_partner(self.partner_id).id,
            ),
            ("reconciled", "=", False),
            ("move_id.state", "=", "posted"),
        ]
        if self.move_type in ("out_invoice", "in_refund"):
            domain.extend([("credit", ">", 0), ("debit", "=", 0)])
            type_payment = _("Outstanding prepayment credits")
        else:
            domain.extend([("credit", "=", 0), ("debit", ">", 0)])
            type_payment = _("Outstanding prepayment debits")
        lines = self.env["account.move.line"].search(domain)
        return lines, type_payment

    def prepayment_assign_move(self, prepayment_aml_id=False, amount=False, date=False):
        """
        This function must be called only when the account of the aml
        is prepayment, in order to generate the assignation move and
        reconcile the transactions.

        Here we don't do any validation, the function must be called
        only when this process should be executed.

        """
        aml_obj = self.env["account.move.line"]
        inv = self
        credit_aml_acc = prepayment_aml_id.account_id.id
        it = inv.move_type
        if it == "in_invoice":
            account = inv.partner_id.property_account_payable_id.id
        elif it == "out_invoice":
            account = inv.partner_id.property_account_receivable_id.id
        else:
            return

        inv_acc = account
        payment = prepayment_aml_id.payment_id
        partner = payment.partner_id
        journal = payment and payment.journal_id or prepayment_aml_id.journal_id
        date = date or fields.Date.context_today(self)

        ref = _(
            "Prepayment Assign of: {}, Inv.: {}".format(
                payment and payment.name or prepayment_aml_id.move_id.name,
                inv.display_name,
            )
        )
        move = (
            self.env["account.move"]
            .with_context(skip_account_move_synchronization=True)
            .create(
                {
                    "date": date,
                    "ref": ref,
                    "company_id": inv.company_id.id,
                    "journal_id": journal.id,
                    "partner_id": partner.id,
                    "prepayment_assignment": True,
                }
            )
        )
        payable_receivable_line = aml_obj.with_context(
            **{
                "check_move_validity": False,
                "skip_account_move_synchronization": True,
            }
        ).create(
            {
                "name": ref,
                "partner_id": partner.id,
                "move_id": move.id,
                "credit": amount if it == "out_invoice" else 0,
                "debit": 0 if it == "out_invoice" else amount,
                "account_id": inv_acc,
                "payment_id": payment.id,
                "date": date,
            }
        )
        advance_line = aml_obj.with_context(
            **{
                "check_move_validity": False,
                "skip_account_move_synchronization": True,
            }
        ).create(
            {
                "name": ref,
                "partner_id": partner.id,
                "move_id": move.id,
                "credit": 0 if it == "out_invoice" else amount,
                "debit": amount if it == "out_invoice" else 0,
                "account_id": credit_aml_acc,
                "payment_id": payment.id,
                "date": date,
            }
        )
        move.with_context(skip_account_move_synchronization=True).action_post()
        acc2rec = advance_line
        acc2rec |= prepayment_aml_id
        acc2rec.reconcile()
        inv.js_assign_outstanding_line(
            payable_receivable_line.id,
        )
        return True

    def button_prepayment_assign(self):
        module = __name__.split("addons.")[1].split(".")[0]
        action_name = "{}.action_account_prepayment_assignment".format(module)
        action = self.env.ref(action_name).read()[0]
        lines, type_payment = self._get_prepayment_lines()
        credit_aml = lines.sorted(lambda x: x.date)[0]
        amount = abs(credit_aml.amount_residual)
        date = fields.Date.context_today(self)
        context = {
            "default_move_id": self.id,
            "default_prepayment_aml_id": credit_aml,
            "default_amount": amount,
            "default_date": date,
        }
        action.update({"context": context})
        return action

    def js_remove_outstanding_partial(self, partial_id):
        res = super().js_remove_outstanding_partial(partial_id)
        if self.prepayment_assignment:
            self.button_draft()
            self.with_context(force_delete=True).unlink()
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends("ref", "move_id")
    def name_get(self):
        if "for_prepayment_assignment" in self.env.context:
            res = []
            name = ""
            for row in self:
                name = ""
                if row.payment_id:
                    name += row.payment_id.name
                if abs(row.amount_residual):
                    name += " {} ({} {})".format(
                        row.date,
                        row.company_currency_id.symbol,
                        abs(row.amount_residual),
                    )
                res.append((row.id, name))
            return res
        return super(AccountMoveLine, self).name_get()


class AccountPayment(models.Model):
    _inherit = "account.payment"

    prepayment_account_id = fields.Many2one(
        "account.account",
        string="Prepayment account",
        domain="[('deprecated','=',False), ('prepayment_account','=',True)]",
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="Counterpart for the prepayment move, for example: Prepayment for customers or vendors.",
    )
    is_prepayment = fields.Boolean(
        "Is prepayment?",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    available_invoices = fields.Char(compute="_get_available_invoices")
    batch_payment = fields.Boolean(
        string="Batch Payment", readonly=True, states={"draft": [("readonly", False)]}
    )
    reconcile_invoice_ids = fields.One2many(
        "account.payment.reconcile",
        "payment_id",
        string="Invoices",
        copy=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    @api.depends(
        "journal_id",
        "partner_id",
        "partner_type",
        "is_internal_transfer",
        "destination_journal_id",
        "is_prepayment",
    )
    def _compute_destination_account_id(self):
        for rec in self:
            if not rec.is_prepayment:
                return super(AccountPayment, self)._compute_destination_account_id()
            else:
                rec.destination_account_id = rec.prepayment_account_id

    @api.onchange("prepayment_account_id")
    def _onchange_prepayment_account_id(self):
        if self.prepayment_account_id:
            self.destination_account_id = self.prepayment_account_id

    def _synchronize_from_moves(self, changed_fields):
        for row in self:
            if row.is_prepayment:
                self = self.with_context(skip_account_move_synchronization=True)
        return super(AccountPayment, self)._synchronize_from_moves(changed_fields)

    def action_post(self):
        for row in self:
            if row.is_prepayment:
                self = self.with_context(skip_account_move_synchronization=True)
            if row.batch_payment:
                move_lines = self.env["account.move.line"]
                rec_lines = row.reconcile_invoice_ids.filtered(
                    lambda x: x.amount_paid > 0
                )
                no_valid = self.reconcile_invoice_ids.filtered(
                    lambda x: float_compare(
                        x.amount_paid,
                        x.amount_residual,
                        precision_digits=row.currency_id.decimal_places,
                    )
                    == 1
                )
                if no_valid:
                    raise ValidationError(
                        _(
                            "You cannot pay more than the amount owed in the following invoices: \n{}".format(
                                "\n".join(map(str, no_valid.mapped("invoice_id.name")))
                            )
                        )
                    )
                if rec_lines:
                    for line in rec_lines:
                        invoice_move = line.invoice_id.line_ids.filtered(
                            lambda r: not r.reconciled
                            and r.account_type
                            in ("liability_payable", "asset_receivable")
                        )
                        payment_move = line.payment_id.move_id.line_ids.filtered(
                            lambda r: not r.reconciled
                            and r.account_type
                            in ("liability_payable", "asset_receivable")
                        )
                        move_lines |= invoice_move + payment_move
                        if invoice_move and payment_move and len(rec_lines) > 0:
                            if row.partner_type == "customer":
                                self.env["account.partial.reconcile"].create(
                                    {
                                        "amount": abs(line.amount_paid),
                                        "debit_amount_currency": abs(line.amount_paid),
                                        "credit_amount_currency": abs(line.amount_paid),
                                        "debit_move_id": invoice_move.id,
                                        "credit_move_id": payment_move.id,
                                    }
                                )
                            else:
                                self.env["account.partial.reconcile"].create(
                                    {
                                        "amount": abs(line.amount_paid),
                                        "debit_amount_currency": abs(line.amount_paid),
                                        "credit_amount_currency": abs(line.amount_paid),
                                        "debit_move_id": payment_move.id,
                                        "credit_move_id": invoice_move.id,
                                    }
                                )
        return super(AccountPayment, self).action_post()

    @api.model
    def create(self, vals_list):
        new_self = self
        if vals_list.get("is_prepayment"):
            new_self = self.with_context(skip_account_move_synchronization=True)
        return super(AccountPayment, new_self).create(vals_list)

    @api.depends("partner_id", "payment_type", "partner_type", "reconcile_invoice_ids")
    def _get_available_invoices(self):
        for row in self:
            move_type = {"outbound": "in_invoice", "inbound": "out_invoice"}
            exclude = []
            if row.reconcile_invoice_ids:
                exclude = row.reconcile_invoice_ids.mapped("invoice_id.id")
            move_domain = [
                ("partner_id", "=", row.partner_id.id),
                ("state", "=", "posted"),
                ("payment_state", "not in", ["paid", "reversed", "in_payment"]),
                ("move_type", "=", move_type[row.payment_type]),
            ]
            if exclude:
                move_domain.extend([("id", "not in", exclude)])
            moves = self.env["account.move"].sudo().search(move_domain)
            if moves:
                move_domain.extend([("id", "in", moves.ids)])
            row.available_invoices = dumps(move_domain)
        return True

    @api.onchange("reconcile_invoice_ids")
    def _onchnage_reconcile_invoice_ids(self):
        self.amount = sum(
            self.reconcile_invoice_ids.filtered(lambda x: x.amount_paid > 0).mapped(
                "amount_paid"
            )
        )

    def button_import_invoices(self):
        if self.state != "draft":
            raise ValidationError(
                _(
                    "This action can only be executed when the payment is in draft status!"
                )
            )
        if self.is_prepayment:
            raise ValidationError(_("This option cannot be used for advance payments!"))
        if self.reconcile_invoice_ids:
            self.reconcile_invoice_ids.unlink()
        module = __name__.split("addons.")[1].split(".")[0]
        action_name = "{}.action_account_payment_import_invoices".format(module)
        action = self.sudo().env.ref(action_name, False).read()[0]
        action["context"] = {"default_payment_id": self.id, "default_state": "draft"}
        return action


class AccountPaymentReconcile(models.Model):
    """Payment invoice detail"""

    _name = "account.payment.reconcile"
    _description = __doc__

    def _check_full_deduction(self):
        if self.invoice_id:
            payment_ids = [
                payment["account_payment_id"]
                for payment in self.invoice_id._get_reconciled_info_JSON_values()
            ]
            if payment_ids:
                payments = self.env["account.payment"].browse(payment_ids)
                return any(
                    [
                        True if payment.tds_amt or payment.sales_tds_amt else False
                        for payment in payments
                    ]
                )
            else:
                return False

    @api.onchange("invoice_id")
    def _onchange_invoice_id(self):
        if self.invoice_id:
            residual = self.invoice_id.amount_residual
            vals = {
                "already_paid": sum(
                    [
                        payment["amount"]
                        for payment in self.invoice_id._get_all_reconciled_invoice_partials()
                    ]
                ),
                "amount_residual": residual,
                "amount_untaxed": self.invoice_id.amount_untaxed,
                "amount_tax": self.invoice_id.amount_tax,
                "currency_id": self.invoice_id.currency_id.id,
                "amount_total": self.invoice_id.amount_total,
                "amount_paid": residual,
            }
            self.update(vals)

    payment_id = fields.Many2one("account.payment")
    reconcile = fields.Boolean(string="Select")
    available_invoices = fields.Char(related="payment_id.available_invoices")
    invoice_id = fields.Many2one("account.move")
    currency_id = fields.Many2one("res.currency")
    amount_total = fields.Monetary(string="Total")
    amount_untaxed = fields.Monetary(string="Untaxed Amount")
    amount_tax = fields.Monetary(string="Taxes Amount")
    already_paid = fields.Float("Amount Paid")
    amount_residual = fields.Monetary("Amount Due")
    amount_paid = fields.Monetary(string="Payment Amount")
