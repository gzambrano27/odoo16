"""
Created on Nov 12, 2020

@author: Zuhair Hammadi
"""
from json import dumps

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class AccountBankStatement(models.Model):
    _name = "account.bank.statement"
    _inherit = ["account.bank.statement", "mail.thread", "mail.activity.mixin"]

    name = fields.Char(default="/", tracking=True)
    state = fields.Selection(
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        selection=[
            ("open", "New"),
            ("confirm", "Validated"),
        ],
        default="open",
    )
    balance_start = fields.Monetary(tracking=True)
    balance_end_real = fields.Monetary(tracking=True)
    line_count = fields.Integer(compute="_calc_line_count")
    is_reconciled = fields.Boolean(
        string="Is Reconciled",
        compute="_compute_is_reconciled",
        store=True,
    )
    journal_type = fields.Selection(
        related="journal_id.type",
        default=lambda self: self._context.get("journal_type"),
        inverse="_inverse_journal_type",
    )

    @api.depends("line_ids.internal_index", "line_ids.state")
    def _compute_date_index(self):
        pass

    def _inverse_journal_type(self):
        pass

    @api.depends("line_ids.is_reconciled")
    def _compute_is_reconciled(self):
        for record in self:
            record.is_reconciled = record.line_ids and all(
                record.mapped("line_ids.is_reconciled")
            )

    @api.depends("line_ids.journal_id")
    def _compute_journal_id(self):
        for statement in self:
            statement.journal_id = statement.line_ids.journal_id or statement.journal_id

    def button_validate(self):
        self.ensure_one()
        if (
            float_compare(
                self.balance_end_real,
                self.balance_end,
                precision_digits=self.currency_id.decimal_places,
            )
            != 0
        ):
            raise ValidationError(
                _(
                    f"The calculated balance {self.balance_end} does not match the real balance {self.balance_end_real}, please check!"
                )
            )
        if self.state != "open" and not self.is_reconciled:
            raise UserError(_("Cannot validate bank statement"))
        self.state = "confirm"
        return True

    def button_reopen(self):
        self.state = "open"

    @api.depends("line_ids")
    def _calc_line_count(self):
        for record in self:
            record.line_count = len(record.line_ids)

    def action_view_lines(self):
        ref = lambda name: self.env.ref(name).id
        return {
            "type": "ir.actions.act_window",
            "name": _("Transactions"),
            "res_model": "account.bank.statement.line",
            "view_mode": "tree,form",
            "views": [
                (
                    ref(
                        "bank_reconciliation.view_bank_statement_line_tree_reconciliation"
                    ),
                    "tree",
                ),
                (
                    ref(
                        "bank_reconciliation.view_bank_statement_line_form_reconciliation"
                    ),
                    "form",
                ),
            ],
            "domain": [("statement_id", "=", self.id)],
            "context": {
                "default_statement_id": self.id,
                "default_journal_id": self.journal_id.id,
            },
        }

    def action_transaction_generate(self):
        move_domain = [
            ("date", "<=", fields.Date.to_string(self.date)),
            ("parent_state", "=", "posted"),
            ("reconciled", "=", False),
            ("journal_id", "=", self.journal_id.id),
            ("account_id", "=", self.journal_id.default_account_id.id),
        ]
        return {
            "type": "ir.actions.act_window",
            "name": _("Generate Transactions"),
            "res_model": "account.bank.statement.generate",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_statement_id": self.id,
                "default_move_domain": dumps(move_domain),
            },
        }

    def action_print(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Print Bank Statement"),
            "res_model": "account.bank.statement.helper",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_statement_id": self.id,
                "default_report_type": "pdf",
            },
        }

    def action_reconcile(self, line_id=None):
        line_ids = self.line_ids
        if line_id is not None:
            index = line_ids.ids.index(line_id.id)
            line_ids = line_ids[index + 1 :]
        for line in line_ids:
            if not line.is_reconciled:
                try:
                    line.with_context(
                        skip_account_move_synchronization=True, reconcile_all_line=True
                    ).action_reconcile()
                except UserError:
                    return line.with_context(
                        reconcile_all_line=True
                    ).button_reconciliation()
                if (
                    line.matched_move_line_ids
                    and not line.matched_move_line_ids.reconciled
                ):
                    line.matched_move_line_ids.with_context(
                        skip_account_move_synchronization=True
                    ).write({"reconciled": True, "statement_id": line.statement_id.id})
            if line.move_id and line.move_id.state != "cancel":
                line.move_id.with_context(
                    skip_account_move_synchronization=True
                ).button_cancel()

    @api.depends(
        "balance_start", "line_ids", "line_ids.amount", "line_ids.reconcile_state"
    )
    def _compute_balance_end(self):
        for stmt in self:
            lines = stmt.line_ids.filtered(lambda x: x.reconcile_state == "Reconciled")
            stmt.balance_end = stmt.balance_start + sum(lines.mapped("amount"))
        return True
