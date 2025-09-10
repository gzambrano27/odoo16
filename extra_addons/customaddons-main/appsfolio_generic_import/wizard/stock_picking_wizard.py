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

from odoo import models, fields, api, _

logging.basicConfig(level=logging.INFO)
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
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


class StockPickingWizard(models.TransientModel):
    _name = "stock.picking.wizard"
    _description = "Stock Picking Wizard"

    file = fields.Binary('File')
    file_import_type = fields.Selection(
        [('csv', 'CSV File'),
         ('xls', 'XLS File')],
        string='Select',
        default='csv'
    )
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        'Picking Type'
    )
    location_id = fields.Many2one(
        'stock.location',
        "Source Location Zone",
        default=lambda self: self.env['stock.picking.type'].browse(
            self._context.get('default_picking_type_id')).default_location_src_id,
        required=True,
    )
    location_dest_id = fields.Many2one(
        'stock.location',
        "Destination Location Zone",
        default=lambda self: self.env['stock.picking.type'].browse(
            self._context.get('default_picking_type_id')).default_location_dest_id,
        required=True,
    )
    picking_type_code = fields.Selection(
        [('incoming', 'Vendors'),
         ('outgoing', 'Customers'),
         ('internal', 'Internal')],
        related='picking_type_id.code'
    )
    option_import_file_by = fields.Selection(
        [('barcode', 'Barcode'),
         ('code', 'Code'),
         ('name', 'Name')],
        string='Import Product By ',
        default='name'
    )

    def check_import_data_character(self, test):
        string_check = re.compile('@')
        if (string_check.search(str(test)) == None):
            return False
        else:
            return True

    def import_picking(self):
        if not self.file:
            raise ValidationError(_("Please select a file first then proceed"))

        if self.file_import_type == 'csv':
            try:
                keys = ['name', 'customer', 'origin', 'date', 'product', 'quantity', 'lot']
                data = base64.b64decode(self.file)
                file_input = io.StringIO(data.decode("utf-8"))
                file_input.seek(0)
                reader_info = list(csv.reader(file_input, delimiter=','))
            except Exception:
                raise ValidationError(_("Invalid File!"))

            picking_ids = []
            for i, row in enumerate(reader_info):
                if i == 0:
                    continue
                values = self._prepare_picking_values(keys, row)
                res = self.create_picking(values)
                picking_ids.append(res)

        else:
            try:
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.file))
                fp.seek(0)
                values = {}
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
            except Exception:
                raise ValidationError(_("Invalid File!"))

            picking_ids = []
            for row_no in range(sheet.nrows):
                if row_no == 0:
                    line_fields = list(map(lambda row: row.value.encode('utf-8'), sheet.row(row_no)))
                else:
                    line = list(
                        map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value),
                            sheet.row(row_no)))
                    values = self._prepare_picking_values_from_xls(line, line_fields, workbook)
                    res = self.create_picking(values)
                    picking_ids.append(res)

        return picking_ids

    def _prepare_picking_values(self, keys, field_values):
        """Prepare values for creating picking."""
        values = dict(zip(keys, field_values))
        values.update({
            'picking_type_id': self.picking_type_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id
        })
        return values

    def _prepare_picking_values_from_xls(self, line, line_fields, workbook):
        """Prepare values for creating picking from XLS."""
        date_string = False
        if line[3] != '':
            if line[3].split('/'):
                if len(line[3].split('/')) > 1:
                    raise ValidationError(_('Date format should be YYYY-MM-DD.'))
                if len(line[3]) > 8 or len(line[3]) < 5:
                    raise ValidationError(_('Date format should be YYYY-MM-DD.'))
            a1 = int(float(line[3]))
            a1_as_datetime = datetime(*xlrd.xldate_as_tuple(a1, workbook.datemode))
            date_string = a1_as_datetime.date().strftime('%Y-%m-%d')

        values = {
            'name': line[0],
            'customer': line[1],
            'origin': line[2],
            'product': line[4],
            'quantity': line[5],
            'date': date_string,
            'picking_type_id': self.picking_type_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'lot': line[6].split('.')[0]
        }

        count = 0
        for l_fields in line_fields:
            if count > 6:
                values.update({
                    l_fields: line[count]
                })
            count += 1

        return values

    def check_partner(self, name):
        """Check if partner exists; create if not."""
        partner_obj = self.env['res.partner']
        partner_search = partner_obj.seacrh([('name', '=', name)])
        if partner_search:
            return partner_search
        else:
            partner_id = partner_obj.create({'name': name})
            return partner_id

    def create_picking(self, values):
        picking_obj = self.env['stock.picking']
        picking_search = picking_obj.search([
            ('name', '=', values.get('name'))
        ])
        pick_id = False
        if picking_search:
            if picking_search.partner_id.name == values.get('customer'):
                pick_id = picking_search[0]
                lines = self.make_picking_line(values, picking_search)
                return lines
            else:
                raise ValidationError(
                    _('Customer name is different for "%s" .\n Please define same.') % values.get('name'))
        else:
            partner_id = self.check_partner(values.get('customer'))
            pick_date = self._get_date(values.get('date'))
            vals = {
                'name': values.get('name'),
                'partner_id': partner_id.id,
                'scheduled_date': pick_date,
                'picking_type_id': values.get('picking_type_id'),
                'location_id': values.get('location_id'),
                'location_dest_id': values.get('location_dest_id'),
                'origin': values.get('origin'),
                'import_data': True,
                'company_id': self.env.context.get('company_id') or self.env.user.company_id.id
            }

            main_list = values.keys()
            for i in main_list:
                model_id = self.env['ir.model'].search([
                    ('model', '=', 'stock.picking')
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
                                                _('"%s" this custom field value "%s" not available') % (
                                                    i, values.get(i)))
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
                                                        _('"%s" This custom field value "%s" not available in system') % (
                                                            i, name))
                                                m2m_value_lst.append(m2m_id.id)

                                        elif ',' in values.get(i):
                                            m2m_names = values.get(i).split(',')
                                            for name in m2m_names:
                                                m2m_id = self.env[many2x_fields.relation].search([
                                                    ('name', '=', name)
                                                ])
                                                if not m2m_id:
                                                    raise ValidationError(
                                                        _('"%s" this custom field value "%s" not available') % (
                                                            i, name))
                                                m2m_value_lst.append(m2m_id.id)

                                        else:
                                            m2m_names = values.get(i).split(',')
                                            m2m_id = self.env[many2x_fields.relation].search([
                                                ('name', 'in', m2m_names)
                                            ])
                                            if not m2m_id:
                                                raise ValidationError(
                                                    _('"%s" this custom field value "%s" not available') % (
                                                        i, m2m_names))
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
                                            _("Wrong value %s for Integer field %s" % (values.get(i), normal_details)))
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
            pick_id = picking_obj.create(vals)
            lines = self.make_picking_line(values, pick_id)
        return pick_id

    def _get_date(self, date):
        if date:
            try:
                i_date = datetime.strptime(date, "%Y-%m-%d").date()
            except Exception:
                raise ValidationError(_('Date format should be YYYY-MM-DD.'))
            return i_date
        else:
            raise ValidationError(_('Please add date field in shhet.'))

    def make_picking_line(self, values, pick_id):
        """Create stock move and move line for picking."""
        product_obj = self.env['product.product']
        stock_lot_obj = self.env['stock.lot']
        stock_move_obj = self.env['stock.move']
        stock_move_line_obj = self.env['stock.move.line']

        product_search_field = {
            'barcode': 'barcode',
            'code': 'default_code',
            'name': 'name'
        }[self.option_import_file_by]

        product_id = product_obj.search([(product_search_field, '=', values.get('product'))], limit=1)

        if not product_id:
            raise ValidationError(_('Product not available: "%s"') % values.get('product'))

        product_lot = False
        if values.get('lot') != '':
            if values.get('lot'):
                lot_id = stock_lot_obj.search([
                    ('name', '=', values.get('lot'))
                ])
                product_lot = lot_id

            if product_lot and not product_lot:
                raise ValidationError(
                    _('%s Lot not available for "%s" Product.') % (values.get('lot'), values.get('product')))

                # Create stock move
            res = stock_move_obj.create({
                'product_id': product_id.id,
                'name': product_id.name,
                'product_uom_qty': values.get('quantity'),
                'picking_id': pick_id.id,
                'location_id': pick_id.location_id.id,
                'date': pick_id.scheduled_date,
                'location_dest_id': pick_id.location_dest_id.id,
                'product_uom': product_id.uom_id.id,
                'picking_type_id': self.picking_type_id.id
            })

            # Create stock move line
            res = stock_move_line_obj.create({
                'picking_id': pick_id.id,
                'location_id': pick_id.location_id.id,
                'location_dest_id': pick_id.location_dest_id.id,
                'qty_done': values.get('quantity'),
                'product_id': product_id.id,
                'move_id': res.id,
                'lot_id': product_lot.id if product_lot else False,
                'product_uom_id': product_id.uom_id.id,
            })

            return True

    @api.onchange('picking_type_id')
    def onchange_picking_type_id(self):
        """Update source and destination locations based on the selected picking type."""
        if self.picking_type_id:
            self.location_id = self.picking_type_id.default_location_src_id.id
            self.location_dest_id = self.picking_type_id.default_location_dest_id.id
