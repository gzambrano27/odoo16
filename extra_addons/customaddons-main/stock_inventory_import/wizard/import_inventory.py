# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api, _
import base64
import csv
import io

class ImportInventory(models.TransientModel):
    _name = 'import.inventory'
    _description = 'Import inventory'

    def _get_default_location(self):
        inventory = self.env['stock.inventory'].browse(self.env.context.get('active_id'))
        return inventory.location_id or self.env['stock.location']

    data = fields.Binary('File', required=True)
    name = fields.Char('Filename')
    delimiter = fields.Char('Delimiter', default=',', help='Default delimiter is ","')
    location = fields.Many2one('stock.location', 'Default Location', default=_get_default_location, required=True)
    date = fields.Datetime('Date')

    def action_import(self):
        """Load Inventory data from the CSV file."""
        inventory_obj = self.env['stock.inventory']
        inv_import_line_obj = self.env['stock.inventory.import.line']
        product_obj = self.env['product.product']

        inventory = inventory_obj.browse(self.env.context.get('active_id'))
        if not inventory:
            raise exceptions.UserError(_("No active inventory found."))

        # Decode the file data
        data = base64.b64decode(self.data)
        file_input = io.StringIO(data.decode('utf-8'))
        location = self.location
        delimiter = self.delimiter or ','
        reader_info = []
        reader = csv.reader(file_input, delimiter=delimiter)

        try:
            reader_info.extend(reader)
        except Exception:
            raise exceptions.UserError(_("Not a valid file!"))

        keys = reader_info[0]
        if not isinstance(keys, list) or ('code' not in keys or 'quantity' not in keys):
            raise exceptions.UserError(_("Not 'code' or 'quantity' keys found"))

        reader_info.pop(0)  # Remove header
        inv_name = u'{} - {}'.format(self.name, fields.Date.today())
        inventory.write({
            'name': inv_name,
            'date': self.date,
            'imported': True,
            'state': 'confirm',
        })

        lines = {
            ':'.join([l.code, l.lot or '', str(l.location_id.id or '')]): l
            for l in inventory.import_lines
        }

        for field in reader_info:
            values = dict(zip(keys, field))
            prod_location = location.id
            if values.get('location'):
                locations = self.env['stock.location'].search([('name', '=', values['location'])])
                if locations:
                    prod_location = locations[0].id

            product = product_obj.search([('default_code', '=', values['code'])], limit=1)
            if product:
                line_vals = {
                    'product': product.id,
                    'code': values['code'],
                    'quantity': float(values['quantity']),
                    'location_id': prod_location,
                    'inventory_id': inventory.id,
                    'fail': True,
                    'fail_reason': _('No processed'),
                }
                if values.get('standard_price'):
                    line_vals['standard_price'] = float(values['standard_price'])

                line_id = ':'.join([values['code'], values.get('lot', ''), str(prod_location)])
                if line_id in lines:
                    lines[line_id].quantity += float(values['quantity'])
                else:
                    inv_import_line_obj.create(line_vals)

class StockInventoryImportLine(models.Model):
    _name = "stock.inventory.import.line"
    _description = "Stock Inventory Import Line"

    code = fields.Char('Product Code')
    product = fields.Many2one('product.product', 'Found Product')
    quantity = fields.Float('Quantity')
    inventory_id = fields.Many2one('stock.inventory', 'Inventory', readonly=True)
    location_id = fields.Many2one('stock.location', 'Location')
    lot = fields.Char('Product Lot')
    fail = fields.Boolean('Fail')
    fail_reason = fields.Char('Fail Reason')
    standard_price = fields.Float(string='Cost Price')
