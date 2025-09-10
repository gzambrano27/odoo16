# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    change_payment = fields.Boolean("Cuentas de Contrapartida", default=False)
    reversed_payment_id = fields.Many2one('account.payment', 'Documento de Reverso', copy=False)
    payment_line_ids = fields.One2many('account.payment.lines', 'payment_id', string="Cuentas",copy=True, store=True)

    other_debit_total = fields.Monetary("Debito", store=True, compute="get_payment_line_amount_real_onchange")
    other_credit_total = fields.Monetary("Crédito", store=True, compute="get_payment_line_amount_real_onchange")

    other_amount_total = fields.Monetary(string="Total", store=True, compute="get_payment_line_amount_real_onchange")
    other_amount_diference = fields.Monetary(string="Diferencia", store=True,
                                             compute="get_payment_line_amount_real_onchange")

    show_line_ids = fields.One2many('account.move.line', compute="_compute_show_line_ids", store=False, readonly=True)

    reversed_payment_ids = fields.One2many('account.payment','reversed_payment_id', 'Documento de Reverso', copy=False)

    reversed_payment_count = fields.Integer(
        string="Cantidad de Documentos de Reverso",
        compute="_compute_reversed_payment_count",
        store=True
    )

    @api.depends('reversed_payment_ids')
    def _compute_reversed_payment_count(self):
        for rec in self:
            rec.reversed_payment_count = len(rec.reversed_payment_ids)

    @api.onchange('move_id', 'change_payment', 'move_id.line_ids', 'partner_id', 'payment_line_ids', 'amount',
                  'payment_type', 'date', 'is_internal_transfer', 'is_prepayment', 'prepayment_account_id',
                  'journal_id')
    def onchange_show_line_ids(self):
        self._origin._compute_show_line_ids()

    @api.depends('move_id', 'change_payment', 'move_id.line_ids', 'partner_id', 'payment_line_ids', 'amount',
                 'payment_type', 'date', 'is_internal_transfer', 'is_prepayment', 'prepayment_account_id', 'journal_id')
    def _compute_show_line_ids(self):
        for brw_each in self:
            brw_each.show_line_ids = brw_each.move_id.line_ids

    @api.onchange('is_internal_transfer', 'change_payment', 'partner_id')
    def onchange_payment_partner_id(self):
        payment_line_ids = [(5,)]
        self.payment_line_ids = payment_line_ids

    @api.depends('payment_type', 'is_internal_transfer', 'change_payment', 'payment_line_ids', 'amount',
                 'payment_line_ids.account_id', 'payment_line_ids.partner_id', 'payment_line_ids.debit',
                 'payment_line_ids.credit')
    def get_payment_line_amount_real_onchange(self):
        DEC = 2
        for record in self:
            if not record.is_internal_transfer and record.change_payment:
                amount_total = record.amount
                change_amount = 0.00
                other_debit_total = 0.00
                other_credit_total = 0.00
                for line in record.payment_line_ids:
                    if record.payment_type == 'outbound':
                        amount_total += line.credit
                        change_amount += line.debit
                    else:
                        amount_total += line.debit
                        change_amount += line.credit
                    other_debit_total += line.debit
                    other_credit_total += line.credit
                if record.payment_type == 'outbound':
                    other_credit_total += record.amount
                else:
                    other_debit_total += record.amount
                record.other_debit_total = round(other_debit_total, DEC)
                record.other_credit_total = round(other_credit_total, DEC)
                record.other_amount_total = round(amount_total, DEC)
                record.other_amount_diference = round(amount_total - change_amount, DEC)
            else:
                record.other_amount_total = 0.00
                record.other_amount_diference = 0.00
                record.other_debit_total = 0.00
                record.other_credit_total = 0.00

    @api.onchange('payment_type', 'is_prepayment', 'is_internal_transfer', 'change_payment', 'payment_line_ids',
                  'amount',
                  'payment_line_ids.account_id', 'payment_line_ids.partner_id', 'payment_line_ids.debit',
                  'payment_line_ids.credit')
    def onchange_payment_line_amount_real_onchange(self):
        DEC = 2
        record = self
        if not record.is_internal_transfer and record.change_payment:
            amount_total = record.amount
            change_amount = 0.00
            other_debit_total = 0.00
            other_credit_total = 0.00
            for line in record.payment_line_ids:
                other_debit_total += line.debit
                other_credit_total += line.credit
            if record.payment_type == 'outbound':
                other_credit_total += record.amount
                amount_total = other_credit_total
                change_amount = other_debit_total
            else:
                other_debit_total += record.amount
                amount_total = other_debit_total
                change_amount = other_credit_total
            record.other_debit_total = round(other_debit_total, DEC)
            record.other_credit_total = round(other_credit_total, DEC)
            record.other_amount_total = round(amount_total, DEC)
            record.other_amount_diference = round(amount_total - change_amount, DEC)
        else:
            record.other_amount_total = 0.00
            record.other_amount_diference = 0.00
            record.other_debit_total = 0.00
            record.other_credit_total = 0.00

    def action_post(self):
        values = super(AccountPayment, self).action_post()
        self.validate_account_payment()
        return values

    def validate_account_payment(self):
        for brw_each in self:
            if not brw_each.is_internal_transfer and brw_each.is_prepayment:
                account_id = brw_each.prepayment_account_id
                exists = brw_each.move_id.line_ids.filtered(lambda x: x.account_id == account_id)
                if not exists:
                    raise ValidationError(_("Si el pago es un anticipo la cuenta del asiento debe ser de anticipo"))
        return True

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        fields_list = list(super(AccountPayment, self)._get_trigger_fields_to_synchronize())
        fields_list += ["payment_line_ids", 'is_prepayment', 'prepayment_account_id', 'payment_type',
                        'is_internal_transfer']
        return tuple(fields_list)

    @api.onchange('is_internal_transfer')
    def onchange_is_internal_transfer(self):
        if self.is_internal_transfer:
            self.change_payment = False

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        parent_values = super(AccountPayment, self)._prepare_move_line_default_vals(
            write_off_line_vals=write_off_line_vals)
        if not self.payment_line_ids:
            return parent_values
        values = [parent_values[0]]
        if self.other_amount_diference == 0.00:
            for brw_line in self.payment_line_ids:
                if brw_line.debit != 0.00 or brw_line.credit != 0.00:
                    counterpart_balance = 0.0
                    # if self.payment_type == 'outbound':
                    #     # Receive money.
                    #     counterpart_balance = brw_line.amount
                    # elif self.payment_type == 'inbound':
                    #     # Send money.
                    #     counterpart_balance = -brw_line.amount
                    if brw_line.debit > 0:
                        counterpart_balance = brw_line.debit
                    if brw_line.credit > 0:
                        counterpart_balance = -brw_line.credit
                    counterpart_amount_currency = counterpart_balance
                    copy_values_lines = {
                        'name': brw_line.name,
                        'date_maturity': self.date,
                        'amount_currency': counterpart_amount_currency,
                        'currency_id': brw_line.company_id.currency_id.id,
                        'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
                        'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
                        'partner_id': brw_line.partner_id and brw_line.partner_id.id or self.partner_id.id,
                        'account_id': brw_line.account_id.id,
                    }
                    if brw_line.analytic_id:
                        copy_values_lines["analytic_distribution"]={str(brw_line.analytic_id.id):100.00}
                    values.append(copy_values_lines)
        return values

    def _synchronize_to_moves(self, changed_fields):
        ''' Update the account.move regarding the modified account.payment.
        :param changed_fields: A list containing all modified fields on account.payment.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        if not any(field_name in changed_fields for field_name in self._get_trigger_fields_to_synchronize()):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):
            if not pay.is_internal_transfer and pay.change_payment:
                pay = pay.with_context(skip_account_move_synchronization=True)
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

            # Make sure to preserve the write-off amount.
            # This allows to create a new payment with custom 'line_ids'.

            write_off_line_vals = []
            if liquidity_lines and counterpart_lines and writeoff_lines:
                write_off_line_vals.append({
                    'name': writeoff_lines[0].name,
                    'account_id': writeoff_lines[0].account_id.id,
                    'partner_id': writeoff_lines[0].partner_id.id,
                    'currency_id': writeoff_lines[0].currency_id.id,
                    'amount_currency': sum(writeoff_lines.mapped('amount_currency')),
                    'balance': sum(writeoff_lines.mapped('balance')),
                })

            line_vals_list = pay._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)
            # print(line_vals_list)
            line_ids_commands = [(5,)
                                 # Command.update(liquidity_lines.id, line_vals_list[0]) if liquidity_lines else Command.create(line_vals_list[0]),
                                 # Command.update(counterpart_lines.id, line_vals_list[1]) if counterpart_lines else Command.create(line_vals_list[1])
                                 ]

            # for line in writeoff_lines:
            #    line_ids_commands.append((2, line.id))

            for extra_line_vals in line_vals_list:
                line_ids_commands.append((0, 0, extra_line_vals))

            # Update the existing journal items.
            # If dealing with multiple write-off lines, they are dropped and a new one is generated.

            pay.move_id \
                .with_context(skip_invoice_sync=True) \
                .write({
                'partner_id': pay.partner_id.id,
                'currency_id': pay.currency_id.id,
                'partner_bank_id': pay.partner_bank_id.id,
                'line_ids': line_ids_commands,
            })

    def _synchronize_from_moves(self, changed_fields):
        # EXTENDS account
        if self.change_payment:
            # Constraints bypass when entry is linked to an expense.
            # Context is not enough, as we want to be able to delete
            # and update those entries later on.
            return
        return super()._synchronize_from_moves(changed_fields)

    def action_print(self):
        self.ensure_one()
        return self.env.ref('account_move_print.action_report_journal_entries').report_action(self.move_id)

    def button_open_reversed_payments(self):
        self.ensure_one()
        srch_reversed=self.search([('reversed_payment_id','=',self.id)])
        srch_reversed+=self.reversed_payment_id
        payments_ids = srch_reversed.ids + [-1, -1]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_account_payments_payable"
        )
        action["domain"] = [('id', 'in', payments_ids)]
        return action