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

from odoo.exceptions import ValidationError

from odoo import models, fields, _

_logger = logging.getLogger(__name__)

try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')
try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')
try:
    import cStringIO
except ImportError:
    _logger.debug('Cannot `import cStringIO`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')
try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')


class AccountBankStatementWizard(models.TransientModel):
    _name = "account.bank.statement.wizard"
    _description = "Account Bank Statement Wizard"

    file = fields.Binary(string='File')
    file_type = fields.Selection(
        [('excel', 'Excel'),
         ('csv', 'CSV')
         ])

    def check_partner(self, name):
        """Check Partner"""
        partner_id = self.env['res.partner'].search([
            ('name', '=', name)])
        if partner_id:
            return partner_id.id
        else:
            return

    def check_import_data_character(self, test):
        """check import data character"""
        string_check = re.compile('@')
        if (string_check.search(str(test)) == None):
            return False
        else:
            return True

    def check_currency(self, currency):
        """Check Currency"""
        currency_id = self.env['res.currency'].search([
            ('name', '=', currency)
        ])
        if currency_id:
            return currency_id.id
        else:
            raise ValidationError(
                _(' "%s" Currency are not available.') % currency.decode("utf-8"))

    def import_data_file_type(self):
        """import data"""
        if self.file_type == 'csv':
            self.import_csv_data()
        elif self.file_type == 'excel':
            self.import_excel_data()
        else:
            raise ValidationError('Select File Type')

    def import_csv_data(self):
        keys = ['date', 'ref', 'partner', 'memo', 'amount', 'currency']
        try:
            file_data = base64.b64decode(self.file)
            file_input = io.StringIO(file_data.decode("utf-8"))
            file_input.seek(0)
            reader = csv.DictReader(file_input, delimiter=',')
        except Exception:
            raise ValidationError(_("Invalid File!"))

        for row in reader:
            values = self.process_imported_row(keys, row)
            self.create_account_bank_statement_line(values)

    def import_excel_data(self):
        try:
            fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
            fp.write(binascii.a2b_base64(self.file))
            fp.seek(0)
            workbook = xlrd.open_workbook(fp.name)
            sheet = workbook.sheet_by_index(0)
        except Exception:
            raise ValidationError(_("Invalid File!"))

        keys = [cell.value.lower() for cell in sheet.row(0)]
        for row_no in range(1, sheet.nrows):
            row = dict(zip(keys, sheet.row_values(row_no)))
            values = self.process_imported_row(keys, row)
            self.create_account_bank_statement_line(values)
            self.create_account_bank_statement_line(values)

    def process_imported_row(self, keys, row):
        values = {}
        for key in keys:
            if key in row and row[key]:
                values[key] = row[key]
        return values

    def create_account_bank_statement_line(self, values):
        statement_line_obj = self.env['account.bank.statement.line']
        partner_id = self.check_partner(values.get('partner'))
        currency_id = self.check_partner(values.get('currency')) if values.get('currency') else False
        date = self.check_bank_line_date(values.get('date'))

        vals = {
            'date': date,
            'payment_ref': values.get('memo'),
            'ref': values.get('ref'),
            'partner_id': partner_id,
            'name': values.get('memo'),
            'amount': values.get('amount'),
            'currency_id': currency_id,
            'statement_id': self._context.get('active_id'),
        }

        for key, value in values.items():
            model_id = self.env['ir.model'].search([('model', '=', 'account.bank.statement.line')])
            normal_details = key.decode('utf-8') if isinstance(key, bytes) else key

            if normal_details.startswith('x_'):
                technical_fields_name, any_special = self.get_technical_field_details(normal_details)
                self.handle_technical_field(values, vals, technical_fields_name, any_special)

            else:
                self.handle_normal_field(model_id, normal_details, value, vals)

        statement_line_obj.create(vals)
        return True

    def get_technical_field_details(self, technical_field):
        split_fields_name = technical_field.split("@")
        technical_fields_name = split_fields_name[0]
        any_special = self.check_import_data_character(technical_fields_name)
        return technical_fields_name, any_special

    def handle_technical_field(self, values, vals, technical_fields_name, any_special):
        if any_special:
            many2x_fields = self.get_many2x_fields(technical_fields_name)
            self.handle_many2x_fields(values, vals, technical_fields_name, many2x_fields)

    def get_many2x_fields(self, technical_fields_name):
        model_id = self.env['ir.model'].search([('model', '=', 'account.bank.statement.line')])
        return self.env['ir.model.fields'].search([
            ('name', '=', technical_fields_name),
            ('model_id', '=', model_id.id)
        ])

    def handle_many2x_fields(self, values, vals, technical_fields_name, many2x_fields):
        if many2x_fields.id:
            field_type = many2x_fields.ttype
            if field_type in ['many2one', 'many2many']:
                self.handle_many2x_fields_subtypes(values, vals, technical_fields_name, many2x_fields, field_type)
            else:
                raise ValidationError(_('%s is not a many2one or many2many field') % technical_fields_name)

    def handle_many2x_fields_subtypes(self, values, vals, technical_fields_name, many2x_fields, field_type):
        if field_type == 'many2one':
            self.handle_many2one_field(values, vals, technical_fields_name, many2x_fields)

        elif field_type == 'many2many':
            self.handle_many2many_field(values, vals, technical_fields_name, many2x_fields)

    def handle_many2one_field(self, values, vals, technical_fields_name, many2x_fields):
        if values.get(technical_fields_name):
            fetch_m2o = self.env[many2x_fields.relation].search([('name', '=', values.get(technical_fields_name))])
            if fetch_m2o.id:
                vals.update({technical_fields_name: fetch_m2o.id})
            else:
                raise ValidationError(
                    _('"%s" this custom field value "%s" not available') % (
                        technical_fields_name, values.get(technical_fields_name)))

    def handle_many2many_field(self, values, vals, technical_fields_name, many2x_fields):
        m2m_value_lst = []
        if values.get(technical_fields_name):
            m2m_names = values.get(technical_fields_name).split(';') if ';' in values.get(
                technical_fields_name) else values.get(technical_fields_name).split(',')
            for name in m2m_names:
                m2m_id = self.env[many2x_fields.relation].search([('name', '=', name)])
                if not m2m_id:
                    raise ValidationError(
                        _('"%s" this custom field value "%s" not available') % (technical_fields_name, name))
                m2m_value_lst.append(m2m_id.id)
        vals.update({technical_fields_name: m2m_value_lst})

    def check_bank_line_date(self, date):
        """Check Bank Line Data"""
        DATETIME_FORMAT = "%Y-%m-%d"
        if not date:
            raise ValidationError(_('Please add a date in the sheet.'))
        try:
            line_date = datetime.strptime(date, DATETIME_FORMAT).date()
        except ValueError:
            raise ValidationError(_('Date format should be YYYY-MM-DD.'))

        return line_date
