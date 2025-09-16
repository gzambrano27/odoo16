# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError
from datetime import datetime
from ...message_dialog.tools import FileManager
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager

fileO = FileManager()
dateO = DateManager()
calendarO = CalendarManager()
from datetime import date, timedelta
from odoo.addons.account.models.account_move_line import AccountMoveLine as OldAccountMoveLine
from odoo.exceptions import ValidationError, UserError

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _where_cal(self, domain=None):
        """Genera el dominio condicional si se activa el contexto show_for_payment."""
        if domain is None:
            domain = []
        OBJ_MOVE=self.env["account.move"].sudo()
        if self._context.get("show_for_payment", False):
            company_id = self._context.get("default_company_id", False)
            date_from = self._context.get("default_date_from", False)
            date_to = self._context.get("default_date_to", False)
            partner_ids = self._context.get("default_partner_ids", []) or []
            tipo = self._context.get("default_show_options", False)
            filter_docs = self._context.get('filter_docs', '*')
            not_show_ids = self._context.get("not_show_ids", [])
            not_request_id = self._context.get('not_request_id', False)
            filter_account_ids=[]
            if not_request_id:
                brw_request=self.env["account.payment.analysis.request.wizard"].sudo().browse(not_request_id)
                not_show_ids+=brw_request.request_line_ids.mapped('invoice_line_id').ids
                ###########buscar otras solicitudes abiertas
                srch_requests=self.env["account.payment.request"].sudo().search([('company_id','=',brw_request.company_id.id),
                                                                                 ('state','not in',('cancelled','locked','done')),
                                                                                 ('invoice_line_id','!=',False)
                                                                                 ])
                not_show_ids += srch_requests.mapped('invoice_line_id').ids
                filter_account_ids=brw_request.get_filter_account_ids()
                ###########buscar otras solicitudes abiertas
            print('not_show_ids', not_show_ids)
            result = OBJ_MOVE.search_query_cxp(
                company_id, date_from, date_to, partner_ids, tipo, filter_docs,not_show_ids,filter_account_ids=filter_account_ids
            )
            print(result)
            line_ids = result and list(dict(result)) or [-1, -1]
            domain = [('id', 'in', line_ids)] + domain

        return domain

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = self._where_cal(domain)
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    def _create_reconciliation_partials(self):
        return super(AccountMoveLine,self)._create_reconciliation_partials()

    @api.model
    def _prepare_reconciliation_partials(self, vals_list):
        ''' Prepare the partials on the current journal items to perform the reconciliation.
        Note: The order of records in self is important because the journal items will be reconciled using this order.
        :return: a tuple of 1) list of vals for partial reconciliation creation, 2) the list of vals for the exchange difference entries to be created
        '''
        max_amount = self._context.get('max_amount', None)
        debit_list=[]
        credit_list = []
        debit_sum_residual,credit_sum_residual=0.00,0.00
        ##################################################################################################
        for x in vals_list:
            if x['balance'] > 0.0 or x['amount_currency'] > 0.0:
                if max_amount is not None and debit_sum_residual >= max_amount:
                    continue
                remaining = float(max_amount) - debit_sum_residual if max_amount is not None else None
                residual = abs(x['amount_residual'])
                to_reconcile = min(residual, remaining) if remaining is not None else residual
                sign = 1 if x['amount_residual'] >= 0 else -1
                x['amount_residual'] = sign * to_reconcile
                x['balance'] = sign * to_reconcile
                if 'amount_currency' in x:
                    x['amount_currency'] = sign * to_reconcile
                if 'amount_residual_currency' in x:
                    x['amount_residual_currency'] = sign * to_reconcile
                debit_sum_residual += to_reconcile
                debit_list.append(x)

        for x in vals_list:
            if x['balance'] < 0.0 or x['amount_currency'] < 0.0:
                if max_amount is not None and credit_sum_residual >= max_amount:
                    continue
                remaining = float(max_amount) - credit_sum_residual if max_amount is not None else None
                residual = abs(x['amount_residual'])
                to_reconcile = min(residual, remaining) if remaining is not None else residual
                sign = 1 if x['amount_residual'] >= 0 else -1
                x['amount_residual'] = sign * to_reconcile
                x['balance'] = sign * to_reconcile
                if 'amount_currency' in x:
                    x['amount_currency'] = sign * to_reconcile
                if 'amount_residual_currency' in x:
                    x['amount_residual_currency'] = sign * to_reconcile
                credit_sum_residual += to_reconcile
                credit_list.append(x)
        ####################################################################################################
        debit_vals_list = iter(debit_list)
        credit_vals_list = iter(credit_list)
        debit_vals = None
        credit_vals = None

        partials_vals_list = []
        exchange_data = {}

        while True:

            # ==== Find the next available lines ====
            # For performance reasons, the partials are created all at once meaning the residual amounts can't be
            # trusted from one iteration to another. That's the reason why all residual amounts are kept as variables
            # and reduced "manually" every time we append a dictionary to 'partials_vals_list'.

            # Move to the next available debit line.
            if not debit_vals:
                debit_vals = next(debit_vals_list, None)
                if not debit_vals:
                    break

            # Move to the next available credit line.
            if not credit_vals:
                credit_vals = next(credit_vals_list, None)
                if not credit_vals:
                    break

            # ==== Compute the amounts to reconcile ====

            res = self._prepare_reconciliation_single_partial(debit_vals, credit_vals)
            if res.get('partial_vals'):
                if res.get('exchange_vals'):
                    exchange_data[len(partials_vals_list)] = res['exchange_vals']
                partials_vals_list.append(res['partial_vals'])
            if res['debit_vals'] is None:
                debit_vals = None
            if res['credit_vals'] is None:
                credit_vals = None

        return partials_vals_list, exchange_data

    def remove_move_reconcile(self):
        """ Undo a reconciliation """
        values=super().remove_move_reconcile()
        return values

def new_reconcile(self):
    ''' Reconcile the current move lines all together.
    :return: A dictionary representing a summary of what has been done during the reconciliation:
            * partials:             A recorset of all account.partial.reconcile created during the reconciliation.
            * exchange_partials:    A recorset of all account.partial.reconcile created during the reconciliation
                                    with the exchange difference journal entries.
            * full_reconcile:       An account.full.reconcile record created when there is nothing left to reconcile
                                    in the involved lines.
            * tax_cash_basis_moves: An account.move recordset representing the tax cash basis journal entries.
    '''
    results = {'exchange_partials': self.env['account.partial.reconcile']}
    #print(self._context)
    if not self:
        return results

    not_paid_invoices = self.move_id.filtered(lambda move:
        move.is_invoice(include_receipts=True)
        and move.payment_state not in ('paid', 'in_payment')
    )

    # ==== Check the lines can be reconciled together ====
    company = None
    account = None
    for line in self:
        if line.reconciled:
            raise UserError(_("You are trying to reconcile some entries that are already reconciled."))
        if not line.account_id.reconcile and line.account_id.account_type not in ('asset_cash', 'liability_credit_card'):
            raise UserError(_("Account %s does not allow reconciliation. First change the configuration of this account to allow it.")
                            % line.account_id.display_name)
        if line.move_id.state != 'posted':
            raise UserError(_('You can only reconcile posted entries.'))
        if company is None:
            company = line.company_id
        elif line.company_id != company:
            raise UserError(_("Entries doesn't belong to the same company: %s != %s")
                            % (company.display_name, line.company_id.display_name))
        if account is None:
            account = line.account_id
        elif line.account_id != account:
            raise UserError(_("Entries are not from the same account: %s != %s")
                            % (account.display_name, line.account_id.display_name))

    if self._context.get('reduced_line_sorting'):
        sorting_f = lambda line: (line.date_maturity or line.date, line.currency_id)
    else:
        sorting_f = lambda line: (line.date_maturity or line.date, line.currency_id, line.amount_currency)
    sorted_lines = self.sorted(key=sorting_f)

    # ==== Collect all involved lines through the existing reconciliation ====

    involved_lines = sorted_lines._all_reconciled_lines()
    involved_partials = involved_lines.matched_credit_ids | involved_lines.matched_debit_ids

    # ==== Create partials ====

    partial_no_exch_diff = bool(self.env['ir.config_parameter'].sudo().get_param('account.disable_partial_exchange_diff'))
    sorted_lines_ctx = sorted_lines.with_context(no_exchange_difference=self._context.get('no_exchange_difference') or partial_no_exch_diff)
    sorted_lines_ctx = sorted_lines_ctx.with_context(
        max_amount=self._context.get('max_amount') or None)
    #print(sorted_lines_ctx._context)
    partials = sorted_lines_ctx._create_reconciliation_partials()
    results['partials'] = partials
    involved_partials += partials
    exchange_move_lines = partials.exchange_move_id.line_ids.filtered(lambda line: line.account_id == account)
    involved_lines += exchange_move_lines
    exchange_diff_partials = exchange_move_lines.matched_debit_ids + exchange_move_lines.matched_credit_ids
    involved_partials += exchange_diff_partials
    results['exchange_partials'] += exchange_diff_partials

    # ==== Create entries for cash basis taxes ====

    is_cash_basis_needed = account.company_id.tax_exigibility and account.account_type in ('asset_receivable', 'liability_payable')
    if is_cash_basis_needed and not self._context.get('move_reverse_cancel') and not self._context.get('no_cash_basis'):
        tax_cash_basis_moves = partials._create_tax_cash_basis_moves()
        results['tax_cash_basis_moves'] = tax_cash_basis_moves

    # ==== Check if a full reconcile is needed ====

    def is_line_reconciled(line, has_multiple_currencies):
        # Check if the journal item passed as parameter is now fully reconciled.
        return line.reconciled \
               or (line.company_currency_id.is_zero(line.amount_residual)
                   if has_multiple_currencies
                   else line.currency_id.is_zero(line.amount_residual_currency)
               )

    has_multiple_currencies = len(involved_lines.currency_id) > 1
    if all(is_line_reconciled(line, has_multiple_currencies) for line in involved_lines):
        # ==== Create the exchange difference move ====
        # This part could be bypassed using the 'no_exchange_difference' key inside the context. This is useful
        # when importing a full accounting including the reconciliation like Winbooks.

        exchange_move = self.env['account.move']
        caba_lines_to_reconcile = None
        if not self._context.get('no_exchange_difference'):
            # In normal cases, the exchange differences are already generated by the partial at this point meaning
            # there is no journal item left with a zero amount residual in one currency but not in the other.
            # However, after a migration coming from an older version with an older partial reconciliation or due to
            # some rounding issues (when dealing with different decimal places for example), we could need an extra
            # exchange difference journal entry to handle them.
            exchange_lines_to_fix = self.env['account.move.line']
            amounts_list = []
            exchange_max_date = date.min
            for line in involved_lines:
                if not line.company_currency_id.is_zero(line.amount_residual):
                    exchange_lines_to_fix += line
                    amounts_list.append({'amount_residual': line.amount_residual})
                elif not line.currency_id.is_zero(line.amount_residual_currency):
                    exchange_lines_to_fix += line
                    amounts_list.append({'amount_residual_currency': line.amount_residual_currency})
                exchange_max_date = max(exchange_max_date, line.date)
            exchange_diff_vals = exchange_lines_to_fix._prepare_exchange_difference_move_vals(
                amounts_list,
                company=involved_lines[0].company_id,
                exchange_date=exchange_max_date,
            )

            # Exchange difference for cash basis entries.
            # If we are fully reversing the entry, no need to fix anything since the journal entry
            # is exactly the mirror of the source journal entry.
            if is_cash_basis_needed and not self._context.get('move_reverse_cancel'):
                caba_lines_to_reconcile = involved_lines._add_exchange_difference_cash_basis_vals(exchange_diff_vals)

            # Create the exchange difference.
            if exchange_diff_vals['move_vals']['line_ids']:
                exchange_move = involved_lines._create_exchange_difference_move(exchange_diff_vals)
                if exchange_move:
                    exchange_move_lines = exchange_move.line_ids.filtered(lambda line: line.account_id == account)

                    # Track newly created lines.
                    involved_lines += exchange_move_lines

                    # Track newly created partials.
                    exchange_diff_partials = exchange_move_lines.matched_debit_ids \
                                             + exchange_move_lines.matched_credit_ids
                    involved_partials += exchange_diff_partials
                    results['exchange_partials'] += exchange_diff_partials

        # ==== Create the full reconcile ====
        results['full_reconcile'] = self.env['account.full.reconcile'] \
            .with_context(
                skip_invoice_sync=True,
                skip_invoice_line_sync=True,
                skip_account_move_synchronization=True,
                check_move_validity=False,
            ) \
            .create({
                'exchange_move_id': exchange_move and exchange_move.id,
                'partial_reconcile_ids': [Command.set(involved_partials.ids)],
                'reconciled_line_ids': [Command.set(involved_lines.ids)],
            })

        # === Cash basis rounding autoreconciliation ===
        # In case a cash basis rounding difference line got created for the transition account, we reconcile it with the corresponding lines
        # on the cash basis moves (so that it reaches full reconciliation and creates an exchange difference entry for this account as well)

        if caba_lines_to_reconcile:
            for (dummy, account, repartition_line), amls_to_reconcile in caba_lines_to_reconcile.items():
                if not account.reconcile:
                    continue

                exchange_line = exchange_move.line_ids.filtered(
                    lambda l: l.account_id == account and l.tax_repartition_line_id == repartition_line
                )

                (exchange_line + amls_to_reconcile).filtered(lambda l: not l.reconciled).reconcile()

    not_paid_invoices.filtered(lambda move:
        move.payment_state in ('paid', 'in_payment')
    )._invoice_paid_hook()

    return results

OldAccountMoveLine.reconcile=new_reconcile