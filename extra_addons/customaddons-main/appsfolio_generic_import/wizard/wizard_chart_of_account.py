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
import tempfile

from odoo.exceptions import UserError

from odoo import models, fields, _

_logger = logging.getLogger(__name__)

try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')
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


class ImportChartAccount(models.TransientModel):
    _name = "import.chart.account"
    _description = "Import Chart of Account"

    select_file = fields.Binary(string="Select File")
    import_file_type = fields.Selection(
        [('csv', 'CSV File'),
         ('xls', 'XLS File')
         ], string='Select', default='csv')

    def import_file(self):
        if self.import_file_type == 'csv':
            keys, file_reader = self.read_csv_file()
        elif self.import_file_type == 'xls':
            keys, file_reader = self.read_xls_file()
        else:
            raise UserError(_("Please select either xls or csv format!"))

        for row_values in file_reader:
            values = dict(zip(keys, row_values))
            res = self.create_chart_accounts(values)

        return res

    def read_csv_file(self):
        keys = [
            'code',
            'name',
            'user_type_id'
        ]
        try:
            csv_data = base64.b64decode(self.select_file)
            data_file = io.StringIO(csv_data.decode("utf-8"))
            data_file.seek(0)
            file_reader = list(csv.reader(data_file, delimiter=','))
        except Exception as e:
            raise UserError(_("Invalid file! Error: %s" % str(e)))

        return keys, file_reader

    def read_xls_file(self):
        try:
            fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            fp.write(binascii.a2b_base64(self.select_file))
            fp.seek(0)
            workbook = xlrd.open_workbook(fp.name)
            sheet = workbook.sheet_by_index(0)
            keys = [str(cell.value) for cell in sheet.row(0)]
            file_reader = [sheet.row_values(row) for row in range(1, sheet.nrows)]
        except Exception as e:
            raise UserError(_("Invalid file! Error: %s" % str(e)))

        return keys, file_reader

    def create_chart_accounts(self, values):
        # Validate mandatory fields
        for field in ["code", "name", "user"]:
            if not values.get(field):
                raise UserError(_('%s field cannot be empty.') % field.capitalize())

        # Truncate trailing zeros from the code
        code_no = str(values.get("code")).rstrip('0').rstrip('.') if '.' in str(values.get("code")) else str(
            values.get("code"))

        # Find account type
        account_type = values.get("user")
        account_search = self.env['account.account'].search([('account_type', '=', account_type)])

        # Set reconcile and deprecated flags
        is_reconcile = values.get("reconcile") in ['TRUE', '1']
        is_deprecated = values.get("deprecat") in ['TRUE', '1']

        # Find currency and group
        currency_get = self.find_currency(values.get('currency'))
        group_get = self.find_group(values.get('group'))

        # Find taxes and tags
        tax_ids = self.find_objects('account.tax', 'tax', values.get('tax'))
        tag_ids = self.find_objects('account.account.tag', 'tag', values.get('tag'))

        # Create account
        data = {
            'code': code_no,
            'name': values.get('name'),
            'account_type': account_type,
            'tax_ids': [(6, 0, [tax.id for tax in tax_ids])] if tax_ids else False,
            'tag_ids': [(6, 0, [tag.id for tag in tag_ids])] if tag_ids else False,
            'group_id': group_get.id,
            'currency_id': currency_get.id if currency_get else False,
            'reconcile': is_reconcile,
            'deprecated': is_deprecated,
            'import_data': True,
        }
        chart_id = self.env['account.account'].create(data)
        return chart_id

    def find_objects(self, model, field, names):
        objects = []
        if names:
            seperator = ';' if ';' in names else ','
            for name in names.split(seperator):
                obj = self.env[model].search([('name', '=', name)])
                if not obj:
                    raise UserError(_('%s "%s" not found in your system') % (field.capitalize(), name))
                objects.extend(obj)
        return objects

    def find_user_type(self, user):
        """Find user type by name.
                Args:
                    user (str): Name of the user.
                Returns:
                    account.account: User account if found.
                Raises:
                    UserError: If user is not provided or not found.
        """
        if not user:
            raise UserError(_("Field User is not correctly set."))

        user_account = self.env['account.account'].search([('name', '=', user)], limit=1)
        if user_account:
            return user_account
        else:
            raise UserError(_("User with name '%s' not found.") % user)

    def find_currency(self, name):
        """Find Currency"""
        if not name:
            return None
        currency = self.env['res.currency'].search([('name', '=', name)], limit=1)
        if currency:
            return currency.id
        else:
            raise UserError(_('Currency "%s" is not available.') % name)

    def find_group(self, group):
        """Find Group"""
        group_type = self.env['account.group']
        group_search = group_type.search([
            ('name', '=', group)
        ])
        if group_search:
            return group_search
        else:
            group_id = group_type.create({
                'name': group
            })
            return group_id
