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
from datetime import date, datetime

import xlrd
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


class VendorPricelistWizard(models.TransientModel):
    _name = "vendor.pricelist.wizard"
    _description = "Vendor Pricelist Wizard"

    file = fields.Binary('File')
    file_import_type = fields.Selection(
        [('csv', 'CSV File'),
         ('xls', 'XLS File')],
        string='Select',
        default='csv'
    )
    option_import_file_by = fields.Selection(
        [('name', 'Name'),
         ('code', 'Code'),
         ('barcode', 'Barcode')],
        string='Select Product By',
        default='name'
    )
    import_prod_variant_option = fields.Selection(
        [('name', 'Name'),
         ('code', 'Code'),
         ('barcode', 'Barcode')],
        string='Select Product Variant BY',
        default='name'
    )

    def check_import_data_character(self, test):
        string_check = re.compile('@')
        if (string_check.search(str(test)) == None):
            return False
        else:
            return True

    def import_vendor_pricelist(self):
        if not self.file:
            raise ValidationError(_('Please select a file.'))

        if self.file_import_type == 'csv':
            keys, file_reader = self.read_csv_file()
        elif self.file_import_type == 'xls':
            keys, file_reader = self.read_xls_file()
        else:
            raise ValidationError(_('Invalid file import type.'))

        values = {}
        for index, row in enumerate(file_reader):
            values = dict(zip(keys, map(str, row)))
            if values and index > 0:
                values.update({'option': self.file_import_type})
                res = self.make_pricelist(values)

        return res

    def read_csv_file(self):
        try:
            if not self.file:
                raise ValidationError(_("No file provided."))

            csv_data = base64.b64decode(self.file)
            data_file = io.StringIO(csv_data.decode("utf-8"))
            data_file.seek(0)
            file_reader = list(csv.reader(data_file, delimiter=','))
        except UnicodeError:
            raise ValidationError(_("Invalid CSV encoding. Please use UTF-8 encoding."))
        except Exception as e:
            raise ValidationError(_("Error reading CSV file: %s" % str(e)))

        keys = ['vendor', 'product_template', 'product_variant', 'min_qty', 'price', 'currency', 'date_start',
                'date_end', 'delay']

        return keys, file_reader

    def read_xls_file(self):
        try:
            if not self.file:
                raise ValidationError(_("No file provided."))

            fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            fp.write(binascii.a2b_base64(self.file))
            fp.seek(0)

            workbook = xlrd.open_workbook(fp.name)
            sheet = workbook.sheet_by_index(0)
        except UnicodeError:
            raise ValidationError(_("Invalid XLS encoding. Please use a valid encoding."))
        except xlrd.XLRDError as xlrd_error:
            raise ValidationError(_("Error reading XLS file: %s" % str(xlrd_error)))
        except Exception as e:
            raise ValidationError(_("An unexpected error occurred: %s" % str(e)))
        finally:
            fp.close()

        keys = ['vendor', 'product_template', 'product_variant', 'min_qty', 'price', 'currency', 'date_start',
                'date_end', 'delay']

        file_reader = [list(
            map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value),
                sheet.row(row_no))) for row_no in range(sheet.nrows)]

        return keys, file_reader

    def check_partner(self, name):
        """Check if partner exists; create if not."""
        partner_obj = self.env['res.partner']
        partner_search = partner_obj.seacrh([('name', '=', name)])
        if partner_search:
            return partner_search
        else:
            partner_id = partner_obj.create({'name': name})
            return partner_id

    def check_currency(self, name):

        currency_obj = self.env['res.currency']
        currency_search = currency_obj.search([
            ('name', '=', name)
        ])
        if currency_search:
            return currency_search
        else:
            raise ValidationError(_('Currency "%s" not found.') % name)

    def find_start_date(self, start_date):
        if start_date:
            try:
                date_record = datetime.strptime(start_date, "%Y-%m-%d").date()
            except Exception:
                raise ValidationError(_('Date format should be YYYY-MM-DD.'))
            return date_record
        else:
            raise ValidationError(_('Please add start date field in sheet.'))

    def find_end_date(self, end_date):
        if date:
            try:
                date_record = datetime.strptime(end_date, "%Y-%m-%d").date()
            except Exception:
                raise ValidationError(_('Date format should be YYYY-MM-DD.'))
            return date_record
        else:
            raise ValidationError(_('Please add end date field in sheet.'))

    def make_pricelist(self, values):
        supplier_search = self.env['product.supplierinfo']
        # Validate required fields
        self.validate_required_fields(values)

        # Check and get partner and currency
        partner_id = self.check_partner(values.get('vendor'))
        currency_id = self.check_currency(values.get('currency'))
        # Find products
        product_template_search, product_variant_search = self.find_products(values)

        # Build supplier info values
        vals = self.build_supplier_info_values(values, partner_id, product_template_search, product_variant_search,
                                               currency_id)
        # Update custom fields
        self.update_custom_fields(values, vals, supplier_search)

        # Create supplier info record
        sale_id = supplier_search.create(vals)
        return sale_id

    def validate_required_fields(self, values):
        required_fields = ['vendor', 'product_template', 'product_variant']
        missing_fields = [field for field in required_fields if not values.get(fields)]

        if missing_fields:
            missing_fields_str = ','.join(missing_fields)
            raise ValidationError(f"Missing required fields:{missing_fields_str}")

    def find_products(self, values):
        product_template_search = self.find_product_by_option('product_template', values)
        product_variant_search = self.find_product_by_option('product_variant', values)

        return product_template_search, product_variant_search

    def find_product_by_option(self, option, values):
        product_templ_obj = self.env['product.template']
        field_name = self.get_field_name_for_option(option)
        return self.find_product_by_field(product_templ_obj, field_name, values[option])

    def get_field_name_for_option(self, option):
        if self.option_import_file_by == 'barcode':
            return 'barcode'
        elif self.option_import_file_by == 'code':
            return 'default_code'
        else:
            return 'name'

    def find_product_by_field(self, model, field_name, field_value):
        return model.search([(field_name, '=', field_value)], limit=1)

    def build_supplier_info_values(self, values, partner_id, product_template_search, product_variant_search,
                                   currency_id):
        return {
            'partner_id': partner_id.id,
            'product_tmpl_id': product_template_search.id,
            'product_id': product_variant_search[0].id if product_variant_search else False,
            'min_qty': values.get('min_qty', 1),
            'price': values.get('price', 0),
            'currency_id': currency_id.id,
            'date_start': values.get('date_start', False),
            'date_end': values.get('date_end', False),
            'delay': values.get('delay', 0),
        }

    def update_custom_fields(self, values, vals, supplier_search):
        main_list = values.keys()
        model_id = self.env['ir.model'].search([('model', '=', 'product.supplierinfo')])

        for i in main_list:
            normal_details = i.decode('utf-8') if type(i) == bytes else i

            if normal_details.startswith('x_'):
                self.handle_custom_fields(normal_details, model_id, values, vals, supplier_search)
            else:
                self.handle_normal_fields(normal_details, model_id, values, vals)

    def handle_normal_fields(self, normal_details, model_id, values, vals):
        self.env['ir.model.fields'].search([
            ('name', '=', normal_details),
            ('model_id', '=', model_id.id)
        ])
