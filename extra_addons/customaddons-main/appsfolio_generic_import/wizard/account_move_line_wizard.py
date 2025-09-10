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

    def check_partner(self, partner_name):
        partner_ids = self.env['res.partner'].search([
            ('name', '=', partner_name)
        ])
        if partner_ids:
            partner_id = partner_ids[0]
            return partner_id
        else:
            None

    def check_desc(self, name):
        if name:
            return name
        else:
            return '/'

    def check_currency(self, currency_name):
        currency_ids = self.env['res.currency'].search([('name', '=', currency_name)])

        if not currency_ids:
            return None
        # If there are multiple currency records with the same name, you may want to handle this situation.
        # For now, I'm assuming you want to return the first currency found.
        currency_id = currency_ids[0]
        return currency_id

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
        if values.get('account_code'):
            account_code = values.get('account_code')
            account_id = self.check_account_code(str(account_code))
            if account_id != None:
                vals.update({
                    'account_id': account_id.id
                })
            else:
                raise ValidationError(_('Invalid Account Code %s') % account_code)

        if values.get('currency'):
            currency = values.get('currency')
            if currency != '' and currency != None:
                currency_id = self.check_currency(currency)
                if currency_id != None:
                    vals.update({
                        'currency_id': currency_id.id
                    })
                else:
                    raise ValidationError(_('Currency %s is not available') % currency)

        if values.get('name'):
            desc_name = values.get('name')
            name = self.check_desc(desc_name)
            vals.update({
                'name': name
            })

        if values.get('partner'):
            partner_name = values.get('partner')
            if self.check_partner(partner_name) != None:
                partner_id = self.check_partner(partner_name)
                vals.update({
                    'partner_id': partner_id.id
                })

        if values.get('date_maturity'):
            date = values.get('date_maturity')
            vals.update({
                'date': date
            })

        if values.get('debit') != '':
            vals.update({
                'debit': float(values.get('debit'))
            })
            if float(values.get('debit')) < 0:
                vals.update({
                    'credit': abs(values.get('debit'))
                })
                vals.update({
                    'debit': 0.0
                })
        else:
            vals.update({
                'debit': float('0.0')
            })

        if values.get('name') == '':
            vals.update({
                'name': '/'
            })

        if values.get('credit') != '':
            vals.update({
                'credit': float(values.get('credit'))
            })
            if float(values.get('credit')) < 0:
                vals.update({
                    'debit': abs(values.get('credit'))
                })
                vals.update({
                    'credit': 0.0
                })
        else:
            vals.update({
                'credit': float('0.0')
            })

        if values.get('amount_currency') != '':
            vals.update({
                'amount_currency': float(values.get('amount_currency'))
            })

        main_list = values.keys()
        for i in main_list:
            model_id = self.env['ir.model'].search([
                ('model', '=', 'account.move.line')
            ])
            if type(i) == bytes:
                normal_details = i.decode('utf-8')
            else:
                normal_details = i
            if normal_details.startswith('x_'):
                any_special = self.check_import_data_character(normal_details)
                if any_special:
                    split_fields_name = normal_details.split("@")
                    technical_fields_name = split_fields_name[0]
                    many2x_fields = self.env['ir.model.fields'].search([
                        ('name', '=', technical_fields_name),
                        ('model_id', '=', model_id.id)
                    ])

                    if many2x_fields.id:
                        if many2x_fields.ttype in ['many2one', 'many2many']:
                            if many2x_fields.ttype == "many2one":
                                if values.get(i):
                                    fetch_m2o = self.env[many2x_fields.relation].search([
                                        ('name', '=', values.get(i))
                                    ])
                                    if fetch_m2o.id:
                                        vals.update({
                                            technical_fields_name: fetch_m2o.id
                                        })
                                    else:
                                        raise ValidationError(
                                            _('"%s" this custom field value "%s" not available') % (i, values.get(i)))

                            if many2x_fields.ttype == "many2many":
                                m2m_value_lst = []
                                if values.get(i):
                                    if ';' in values.get(i):
                                        m2m_names = values.get(i).split(';')
                                        for name in m2m_names:
                                            m2m_id = self.env[many2x_fields.relation].search([
                                                ('name', '=', name)
                                            ])
                                            if not m2m_id:
                                                raise ValidationError(
                                                    _('"%s" this custom field value "%s" not available') % (i, name))
                                            m2m_value_lst.append(m2m_id.id)

                                    elif ',' in values.get(i):
                                        m2m_names = values.get(i).split(',')
                                        for name in m2m_names:
                                            m2m_id = self.env[many2x_fields.relation].search([
                                                ('name', '=', name)
                                            ])
                                            if not m2m_id:
                                                raise ValidationError(
                                                    _('"%s" this custom field value "%s" not available') % (i, name))
                                            m2m_value_lst.append(m2m_id.id)

                                    else:
                                        m2m_names = values.get(i).split(',')
                                        m2m_id = self.env[many2x_fields.relation].search([
                                            ('name', 'in', m2m_names)
                                        ])
                                        if not m2m_id:
                                            raise ValidationError(
                                                _('"%s" this custom field value "%s" not available') % (i, m2m_names))
                                        m2m_value_lst.append(m2m_id.id)
                                vals.update({
                                    technical_fields_name: m2m_value_lst
                                })
                        else:
                            raise ValidationError(
                                _('"%s" this custom field type is not many2one/many2many') % technical_fields_name)
                    else:
                        raise ValidationError(
                            _('"%s" this m2x custom field is not available') % technical_fields_name)
                else:
                    normal_fields = self.env['ir.model.fields'].search([
                        ('name', '=', normal_details),
                        ('model_id', '=', model_id.id)
                    ])
                    if normal_fields.id:
                        if normal_fields.ttype == 'boolean':
                            vals.update({
                                normal_details: values.get(i)
                            })
                        elif normal_fields.ttype == 'char':
                            vals.update({
                                normal_details: values.get(i)
                            })
                        elif normal_fields.ttype == 'float':
                            if values.get(i) == '':
                                float_value = 0.0
                            else:
                                float_value = float(values.get(i))
                            vals.update({
                                normal_details: float_value
                            })
                        elif normal_fields.ttype == 'integer':
                            if values.get(i) == '':
                                int_value = 0
                            else:
                                try:
                                    int_value = int(float(values.get(i)))
                                except:
                                    raise ValidationError(
                                        _("Wrong value %s for Integer" % values.get(i)))
                            vals.update({
                                normal_details: int_value
                            })
                        elif normal_fields.ttype == 'selection':
                            vals.update({
                                normal_details: values.get(i)
                            })
                        elif normal_fields.ttype == 'text':
                            vals.update({
                                normal_details: values.get(i)
                            })
                    else:
                        raise ValidationError(
                            _('"%s" this custom field is not available') % normal_details)
        return vals

    def check_account_code(self, account_code):
        if not account_code:
            raise ValidationError(_('Invalid Account Code: %s') % account_code)

        account = self.env['account.account'].search([('code', '=', account_code)], limit=1)
        if account:
            return account
        else:
            raise ValidationError(_('Account with code "%s" not found.') % account_code)
