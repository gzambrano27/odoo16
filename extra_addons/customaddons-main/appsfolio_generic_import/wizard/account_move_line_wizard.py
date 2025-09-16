# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of appsfolio. (Website: www.appsfolio.in).                            #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

import binascii
import io
import logging
import re
import tempfile
from datetime import datetime

import xlrd
from odoo.exceptions import ValidationError

from odoo import models, fields, _

_logger = logging.getLogger(__name__)

try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


class AccountMoveLineWizard(models.TransientModel):
    _name = "account.move.line.wizard"
    _description = "Account Move Line Wizard"

    file = fields.Binary('File')
    file_import_type = fields.Selection(
        [('csv', 'CSV File'),
         ('xls', 'XLS File')
         ], string='Select', default='csv')

    def check_import_data_character(self, test):
        string_check = re.compile('@')
        if (string_check.search(str(test)) == None):
            return False
        else:
            return True

    def check_partner(self, partner_name, company=None):
        """Busca el partner por nombre en la compañía del asiento o compartido."""
        if not partner_name:
            return None
        _, company = self._get_target_move_and_company() if not company else (None, company)
        Partner = self.env['res.partner'].with_context(self._company_ctx(company))
        partner = Partner.search([
            ('name', '=', partner_name),
            '|', ('company_id', '=', company.id),
                ('company_id', '=', False),
        ], limit=1)
        return partner or None

    def check_desc(self, name):
        if name:
            return name
        else:
            return '/'

    def check_currency(self, currency_name):
        if not currency_name:
            return None
        Currency = self.env['res.currency']  # global
        return Currency.search([('name', '=', currency_name)], limit=1) or None
    
    def _get_target_move_and_company(self):
        move = self.env['account.move'].browse(self.env.context.get('active_id'))
        company = move.company_id or self.env.company
        return move, company

    def _company_ctx(self, company):
        # Contexto que fuerza/limita búsquedas a la compañía del asiento
        return dict(self.env.context, allowed_company_ids=[company.id], force_company=company.id)
    
    def _find_analytic_account(self, token, company=None):
        """ID, código o nombre; restringido a la compañía destino o compartido."""
        if not token:
            return False
        token = str(token).strip()
        _, company = self._get_target_move_and_company() if not company else (None, company)
        Analytic = self.env['account.analytic.account'].with_context(self._company_ctx(company))
        dom_company = ['|', ('company_id', '=', False), ('company_id', '=', company.id)]

        if token.isdigit():
            rec = Analytic.search([('id', '=', int(token))] + dom_company, limit=1)
            if rec:
                return rec
        rec = Analytic.search([('code', '=', token)] + dom_company, limit=1)
        if rec:
            return rec
        rec = Analytic.search([('name', '=', token)] + dom_company, limit=1)
        if rec:
            return rec
        return Analytic.search(['|', ('code', 'ilike', token), ('name', 'ilike', token)] + dom_company, limit=1) or False

    def import_move_line_file(self):
        if self.file_import_type == 'csv':
            keys = ['name',
                    'partner',
                    'analytic_account_id',
                    'account_code',
                    'date_maturity',
                    'debit',
                    'credit',
                    'amount_currency',
                    'currency'
                    ]
            try:
                csv_data = base64.b64decode(self.file)
                data_file = io.StringIO(csv_data.decode("utf-8"))
                data_file.seek(0)
                file_reader = []
                csv_reader = csv.reader(data_file, delimiter=',')
                file_reader.extend(csv_reader)
            except Exception:
                raise ValidationError(_("Invalid File!"))

            values = {}
            lines = []
            for i in range(len(file_reader)):
                field = list(map(str, file_reader[i]))
                count = 1
                count_keys = len(keys)
                if len(field) > count_keys:
                    for new_fields in field:
                        if count > count_keys:
                            keys.append(new_fields)
                        count += 1
                values = dict(zip(keys, field))
                if values:
                    if i == 0:
                        continue
                    else:
                        res = self.create_account_move_line(values)
                        lines.append((0, 0, res))

            if self._context:
                if self._context.get('active_id'):
                    move_obj = self.env['account.move']
                    move_record = move_obj.browse(self._context.get('active_id'))
                    move_record.write({
                        'line_ids': lines
                    })

        else:
            try:
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.file))
                fp.seek(0)
                values = {}
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
                product_obj = self.env['product.product']
                lines = []
            except Exception:
                raise ValidationError(_("Invalid File!"))

            for row_no in range(sheet.nrows):
                val = {}
                if row_no <= 0:
                    line_fields = map(
                        lambda row: row.value.encode('utf-8'), sheet.row(row_no))
                else:
                    line = list(map(
                        lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value),
                        sheet.row(row_no)))
                    date = False
                    if line[4] != '':
                        if line[4].split('/'):
                            if len(line[4].split('/')) > 1:
                                raise ValidationError(
                                    _('Date format should be YYYY-MM-DD.'))
                            if len(line[4]) > 8 or len(line[4]) < 5:
                                raise ValidationError(
                                    _('Date format should be YYYY-MM-DD.'))
                    else:
                        raise ValidationError(
                            _('Please provide Maturity date.'))
                    date1 = int(float(line[4]))
                    line_datetime = datetime(*xlrd.xldate_as_tuple(date1, workbook.datemode))
                    date_string = line_datetime.date().strftime('%Y-%m-%d')

                    values = {
                        'name': line[0],
                        'partner': line[1],
                        'analytic_account_id': line[2],  # <--- NUEVO
                        'account_code': line[3],
                        'date_maturity': date_string,
                        'debit': line[5],
                        'credit': line[6],
                        'amount_currency': line[7],
                        'currency': line[8],
                    }
                    count = 0
                    for l_fields in line_fields:
                        if (count > 5):
                            values.update({
                                l_fields: line[count]
                            })
                        count += 1
                    res = self.create_account_move_line(values)
                    lines.append((0, 0, res))

            if self._context:
                if self._context.get('active_id'):
                    move_obj = self.env['account.move']
                    move_record = move_obj.browse(self._context.get('active_id'))
                    move_record.write({
                        'line_ids': lines
                    })

    def create_account_move_line(self, values):
        vals = {}
        move, company = self._get_target_move_and_company()

        # CUENTA CONTABLE (obligatorio y company-dependent)
        if values.get('account_code'):
            account = self.check_account_code(str(values.get('account_code')), company=company)
            vals['account_id'] = account.id
        else:
            raise ValidationError(_('Missing Account Code'))

        # MONEDA (global)
        if values.get('currency'):
            currency = self.check_currency(values.get('currency'))
            if not currency:
                raise ValidationError(_('Currency %s is not available') % values.get('currency'))
            vals['currency_id'] = currency.id

        # DESCRIPCIÓN
        vals['name'] = self.check_desc(values.get('name'))

        # PARTNER (mismo company o compartido)
        if values.get('partner'):
            partner = self.check_partner(values.get('partner'), company=company)
            if not partner:
                # más claro que tomar uno de otra empresa
                raise ValidationError(_("Partner '%s' not found in company '%s' (or shared).")
                                    % (values.get('partner'), company.display_name))
            vals['partner_id'] = partner.id

        # FECHA DE VENCIMIENTO / FECHA
        if values.get('date_maturity'):
            vals['date_maturity'] = values.get('date_maturity')
        if values.get('date_maturity'):
            vals['date'] = values.get('date_maturity')  # opcional; la fecha real la hereda del move

        # ANALÍTICA (misma company o compartida)
        analytic_token = (values.get('analytic_account_id')
                        or values.get('analytic') or values.get('analytic_code'))
        if analytic_token not in (None, '', False):
            analytic_rec = self._find_analytic_account(analytic_token, company=company)
            if not analytic_rec:
                raise ValidationError(_("Analytic account '%s' not found for company '%s'")
                                    % (analytic_token, company.display_name))
            vals['analytic_distribution'] = {analytic_rec.id: 100.0}
            # Si usas también analytic_account_id:
            # vals['analytic_account_id'] = analytic_rec.id

        # DÉBITO / CRÉDITO
        debit = float(values.get('debit') or 0.0)
        credit = float(values.get('credit') or 0.0)
        if debit < 0:
            credit = abs(debit); debit = 0.0
        if credit < 0:
            debit = abs(credit); credit = 0.0
        vals['debit'] = debit
        vals['credit'] = credit

        # IMPORTE EN MONEDA
        if values.get('amount_currency') not in (None, ''):
            vals['amount_currency'] = float(values.get('amount_currency') or 0.0)

        return vals

    def check_account_code(self, account_code, company=None):
        """Cuenta contable por código, en la compañía del asiento."""
        if not account_code:
            raise ValidationError(_('Invalid Account Code: %s') % account_code)
        _, company = self._get_target_move_and_company() if not company else (None, company)
        Account = self.env['account.account'].with_context(self._company_ctx(company))
        account = Account.search([
            ('code', '=', account_code),
            ('company_id', '=', company.id),
        ], limit=1)
        if account:
            return account
        raise ValidationError(_('Account with code "%s" not found in company "%s".') % (account_code, company.display_name))
