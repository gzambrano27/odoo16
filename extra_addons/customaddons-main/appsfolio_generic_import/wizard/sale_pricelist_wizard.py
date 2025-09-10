# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of appsfolio. (Website: www.appsfolio.in).                            #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

import logging
import io
import re
import tempfile
import binascii
import xlrd
from datetime import datetime
from odoo import models, fields,  _
from odoo.exceptions import ValidationError

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
   

class SalePricelistWizard(models.TransientModel):
    _name = "sale.pricelist.wizard"
    _description = "Sale Pricelist Wizard"

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
        string='Select Product Variant By',
        default='name'
    )
    compute_type = fields.Selection(
        [('both', 'Fixed/Percentage'),
        ('formula', 'Formula')],
        string='Compute Type',
        default='both'
    )
    down_samp_file = fields.Boolean(string='Download Sample Files')

    def check_import_data_character(self ,test):
        string_check= re.compile('@')
        return string_check.search(str(test)) is not None

    def import_sale_pricelist(self):
        if not self.file:
            raise ValidationError(_('Please Select a file.'))

        if self.file_import_type == 'csv':
            try:
                keys = ['name', 'currency', 'apply_on', 'check_apply_on', 'min_qty', 'start_dt', 'end_dt']
                if self.compute_type == 'both':
                    keys.extend(['compute_price', 'amount'])
                else:
                    keys.extend(['based_on', 'discount', 'surcharge', 'rounding', 'min_margin', 'max_margin',
                                 'other_pricelist'])

                csv_data = base64.b64decode(self.file)
                data_file = io.StringIO(csv_data.decode("utf-8"))
                data_file.seek(0)
                csv_reader = csv.reader(data_file, delimiter=',')
                file_reader = list(csv_reader)

            except Exception:
                raise ValidationError(_("Invalid file!"))

            values = {}
            for i, row in enumerate(file_reader):
                field = list(map(str, row))

                if i == 0:
                    count = 1
                    count_keys = len(keys)
                    if len(field) > count_keys:
                        for new_fields in field:
                            if count > count_keys:
                                keys.append(new_fields)
                            count += 1
                    continue  # Skip header row

                values = dict(zip(keys, field))
                values.update({'option': self.file_import_type})
                res = self.create_sale_pricelist(values)

        else:
            fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            fp.write(binascii.a2b_base64(self.file))
            fp.seek(0)

            try:
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
            except Exception:
                raise ValidationError(_("Invalid file!"))

            line_fields = list(map(lambda row: row.value.encode('utf-8'), sheet.row(0)))
            for row_no in range(1, sheet.nrows):
                line = list(
                    map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value),
                        sheet.row(row_no)))
                values = self.extract_values_from_excel_row(line, line_fields)
                res = self.create_sale_pricelist(values)

    def extract_values_from_excel_row(self, line, line_fields):
        start_date_string, end_dt_string = False, False

        amount = line[8] or 0
        start_date, end_date = int(float(line[5])), int(float(line[6]))

        if line[5] and line[6]:
            start_dt_datetime = datetime(*xlrd.xldate_as_tuple(start_date, workbook.datemode))
            end_dt_datetime = datetime(*xlrd.xldate_as_tuple(end_date, workbook.datemode))
            start_date_string = start_dt_datetime.date().strftime('%Y-%m-%d')
            end_dt_string = end_dt_datetime.date().strftime('%Y-%m-%d')

        min_qty = int(float(line[4])) if line[4] else 1

        values = {
            'name': line[0],
            'currency': line[1],
            'apply_on': line[2].strip(),
            'check_apply_on': line[3],
            'min_qty': min_qty,
            'start_dt': start_date_string,
            'end_dt': end_dt_string,
        }

        if self.compute_type == 'both':
            values.update({
                'compute_price': line[7],
                'amount': float(amount),
            })
        else:
            discount, surcharge, rounding, min_margin, max_margin = line[8:13]
            values.update({
                'based_on': line[7],
                'discount': float(discount),
                'surcharge': float(surcharge),
                'rounding': float(rounding),
                'min_margin': float(min_margin),
                'max_margin': float(max_margin),
            })

            if line[7].lower() == 'other pricelist' and line[13]:
                values.update({'other_pricelist': line[13]})

        return values

    def check_currency(self, name):
        currency_obj = self.env['res.currency']
        return currency_obj.search([('name', '=', name)])

    def create_sale_pricelist(self, values):
        pricelist_obj = self.env['product.pricelist']

        name = values.get('name')
        currency = values.get('currency')

        if not name:
            raise ValidationError(_("Name is required."))

        pricelist = pricelist_obj.search([('name', '=', name), ('currency_id.name', '=', currency)])

        if pricelist:
            lines = self.create_sale_pricelist_line(values, pricelist)
            pricelist.write({'item_ids': [(4, lines.id)]})
            return pricelist

        currency_id = self.check_currency(currency)
        vals = {'name': name, 'currency_id': currency_id.id if currency_id else False}
        import_data = self.extract_import_data(values)
        vals.update(import_data)

        pricelist = pricelist_obj.create(vals)
        self.update_pricelist_item(values, pricelist)

        return pricelist

    def extract_import_data(self, values):
        import_data = {'import_data': True}
        main_list = values.keys()

        for i in main_list:
            if isinstance(i, bytes):
                i = i.decode('utf-8')

            if i.startswith('x_'):
                import_data.update(self.extract_custom_field_value(i, values.get(i)))
            else:
                import_data.update(self.extract_normal_field_value(i, values.get(i)))

        return import_data

    def extract_custom_field_value(self, field_name, field_value):
        # Implement your logic for extracting custom field values
        # and return a dictionary with the extracted values
        return {}

    def extract_normal_field_value(self, field_name, field_value):
        # Implement your logic for extracting normal field values
        # and return a dictionary with the extracted values
        return {}

    def update_pricelist_item(self, values, pricelist):
        apply_on = values.get('apply_on')
        min_qty = values.get('min_qty') or 1
        start_date = values.get('start_dt')
        end_date = values.get('end_dt')
        compute_type = self.compute_type

        if apply_on or min_qty or start_date or end_date or compute_type:
            lines = self.create_sale_pricelist_line(values, pricelist)
            pricelist.write({'item_ids': [(4, lines.id)]})

    def create_sale_pricelist_line(self, values, pricelist):
        # Implement your logic for creating pricelist lines
        # and return the created line record
        return None

    def check_currency(self, name):
        currency_obj = self.env['res.currency']
        return currency_obj.search([('name', '=', name)])
   
    def create_sale_pricelist_line(self, values, pricelist_id):
        product_obj = self.env['product.product']
        product_templ_obj = self.env['product.template']
        product_categ_obj = self.env['product.category']
        pricelist_obj = self.env['product.pricelist']
        pricelist_line_obj = self.env['product.pricelist.item']
        DATETIME_FORMAT = "%Y-%m-%d"
        current_time=datetime.now().strftime('%Y-%m-%d')
        product_categ = product_categ_obj.search([
            ('name', '=', values.get('check_apply_on'))
        ])
        set_product_template = False
        set_product_variant = False
        apply_on = values.get('apply_on') or 'global'
        min_qty = values.get('min_qty') or 1
        st_date = values.get('start_dt') or current_time
        ed_date = values.get('end_dt') or current_time
        st_dt = datetime.strptime(st_date, DATETIME_FORMAT) 
        ed_dt = datetime.strptime(ed_date, DATETIME_FORMAT)
        compute_type = self.compute_type
        fixed = 0.00
        percentage = 0.00
        other_pricelist_column = False
        if_formula_then_add = {}

        if compute_type == 'both':
            if values['compute_price'].lower() == 'percentage':
                compute_type = 'percentage'
                percentage = values['amount']
            elif values['compute_price'].lower() == 'fix':
                compute_type = 'fixed'
                fixed = values['amount']
            else:
                compute_type = 'fixed'
                fixed = values['amount']
        elif compute_type == 'formula':
            compute_type = 'formula'
            based_on = False
            if values.get('based_on'):
                if values['based_on'].lower() == 'sale price':
                    based_on = 'list_price'
                if values['based_on'].lower() == 'cost':
                    based_on = 'standard_price'
                if values['based_on'].lower() == 'other pricelist':
                    based_on = 'pricelist'
                    if values['other_pricelist']:
                        other_pricelist_column = values['other_pricelist'].lower()
                    else:
                        raise ValidationError(
                            _("Please fill 'Other Pricelist' column in CSV or XLS file."))
                        return

                discount = values['discount']
                surcharge = values['surcharge']
                rounding = values['rounding']
                min_margin = values['min_margin']
                max_margin = values['max_margin']
                if based_on and discount and surcharge and rounding and min_margin and max_margin:
                    if_formula_then_add.update({
                        'based_on': based_on,
                        'discount': discount,
                        'surcharge': surcharge,
                        'rounding': rounding,
                        'min_margin': min_margin,
                        'max_margin': max_margin,
                    })
            else:
                raise ValidationError(
                    _("Please fill the 'Based On' column in CSV or XLS file, if you want to import pricelist using formula."))

        if(apply_on.lower() == 'global'):
            vals = {
                'applied_on':'3_global',
                'min_quantity': min_qty,
                'date_start': st_dt,
                'date_end': ed_dt,
                'compute_price': compute_type,
                'fixed_price': fixed,
                'percent_price': percentage,
            }
            if if_formula_then_add:
                vals.update({
                    'base': if_formula_then_add['based_on'],
                    'price_discount': if_formula_then_add['discount'],
                    'price_surcharge': if_formula_then_add['surcharge'],
                    'price_round': if_formula_then_add['rounding'],
                    'price_min_margin': if_formula_then_add['min_margin'],
                    'price_max_margin': if_formula_then_add['max_margin'],
                })
                if other_pricelist_column:
                    other_pricelist_m2o = pricelist_obj.search([
                        ('name', '=ilike', other_pricelist_column)
                    ])
                    vals.update({
                        'base_pricelist_id': other_pricelist_m2o.id,
                    })

            return_line_obj = pricelist_line_obj.create(vals)
            return return_line_obj

        elif(apply_on.lower() == 'product category'):
            if product_categ:
                vals={
                    'applied_on': '2_product_category',
                    'categ_id': product_categ.id,
                    'min_quantity': min_qty,
                    'date_start': st_dt,
                    'date_end': ed_dt,
                    'compute_price': compute_type,
                    'fixed_price': fixed,
                    'percent_price': percentage,
                }
                if if_formula_then_add:
                    vals.update({
                        'base': if_formula_then_add['based_on'],
                        'price_discount': if_formula_then_add['discount'],
                        'price_surcharge': if_formula_then_add['surcharge'],
                        'price_round': if_formula_then_add['rounding'],
                        'price_min_margin': if_formula_then_add['min_margin'],
                        'price_max_margin': if_formula_then_add['max_margin'],
                    })
                if other_pricelist_column:
                    other_pricelist_m2o = pricelist_obj.search([
                        ('name', '=ilike', other_pricelist_column)
                    ])
                    vals.update({
                        'base_pricelist_id': other_pricelist_m2o.id,
                    })

                return_line_obj = pricelist_line_obj.create(vals)
                return return_line_obj
            else:
                raise ValidationError(
                    _(' "%s" is not a category.') % values['check_apply_on'])

        elif(apply_on.lower() == 'product'):
            if self.option_import_file_by == 'barcode':
                set_product_template = product_templ_obj.search([
                    ('barcode', '=', values['check_apply_on'])
                ])
                if not set_product_template:
                    raise ValidationError(
                        _(' "%s" Product is not available.') % values['check_apply_on'])
            
            elif self.option_import_file_by == 'code':
                set_product_template = product_templ_obj.search([
                    ('default_code', '=', values['check_apply_on'])
                ])
                if not set_product_template:
                    raise ValidationError(
                        _(' "%s" Product is not available.') % values['check_apply_on'])
            
            else:
                set_product_template = product_templ_obj.search([
                    ('name', '=', values['check_apply_on'])
                ])
                if not set_product_template:
                    raise ValidationError(
                        _(' "%s" Product is not available.') % values['check_apply_on'])

            if set_product_template:
                vals={
                    'applied_on':'1_product',
                    'product_tmpl_id' : set_product_template.id,
                    'min_quantity': min_qty,
                    'date_start': st_dt,
                    'date_end': ed_dt,
                    'compute_price': compute_type,
                    'fixed_price': fixed,
                    'percent_price': percentage,
                }
                if if_formula_then_add:
                    vals.update({
                        'base': if_formula_then_add['based_on'],
                        'price_discount': if_formula_then_add['discount'],
                        'price_surcharge': if_formula_then_add['surcharge'],
                        'price_round': if_formula_then_add['rounding'],
                        'price_min_margin': if_formula_then_add['min_margin'],
                        'price_max_margin': if_formula_then_add['max_margin'],
                    })
                if other_pricelist_column:
                    other_pricelist_m2o = pricelist_obj.search([
                        ('name', '=ilike', other_pricelist_column)
                    ])
                    vals.update({
                        'base_pricelist_id': other_pricelist_m2o.id,
                    })

                return_line_obj = pricelist_line_obj.create(vals)
                return return_line_obj

        elif(apply_on.lower() == 'product variant'):
            if self.import_prod_variant_option == 'barcode':
                set_product_variant = product_obj.search([
                    ('barcode', '=', values['check_apply_on'])
                ])
                if not set_product_variant:
                    raise ValidationError(
                        _(' "%s" Product variant is not available.') % values['check_apply_on'])
            
            elif self.import_prod_variant_option == 'code':
                set_product_variant = product_obj.search([
                    ('default_code', '=',values['check_apply_on'])
                ])
                if not set_product_variant:
                    raise ValidationError(
                        _(' "%s" Product varinat is not available.') % values['check_apply_on'])
            
            else:
                set_product_variant = product_obj.search([
                    ('name', '=', values['check_apply_on'])
                ])
                if not set_product_variant:
                    raise ValidationError(
                        _(' "%s" Product variant is not available.') % values['check_apply_on'])

            if set_product_variant:
                vals={
                    'applied_on':'0_product_variant',
                    'product_id': set_product_variant[0].id,
                    'min_quantity': min_qty,
                    'date_start': st_dt,
                    'date_end': ed_dt,
                    'compute_price': compute_type,
                    'fixed_price': fixed,
                    'percent_price': percentage,
                }
                if if_formula_then_add:
                    vals.update({
                        'base': if_formula_then_add['based_on'],
                        'price_discount': if_formula_then_add['discount'],
                        'price_surcharge': if_formula_then_add['surcharge'],
                        'price_round': if_formula_then_add['rounding'],
                        'price_min_margin': if_formula_then_add['min_margin'],
                        'price_max_margin': if_formula_then_add['max_margin'],
                    })
                if other_pricelist_column:
                    other_pricelist_m2o = pricelist_obj.search([
                        ('name', '=ilike', other_pricelist_column)
                    ])
                    vals.update({
                        'base_pricelist_id': other_pricelist_m2o.id,
                    })

                return_line_obj = pricelist_line_obj.create(vals)
                return return_line_obj
