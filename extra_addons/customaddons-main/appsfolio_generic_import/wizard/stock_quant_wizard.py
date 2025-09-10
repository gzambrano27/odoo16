# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of appsfolio. (Website: www.appsfolio.in).                            #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

import io
import logging
from datetime import datetime

from odoo.exceptions import ValidationError

from odoo import exceptions
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
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')
try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')


class StockQuantWizard(models.TransientModel):
    _name = "stock.quant.wizard"
    _description = "Stock Quant Wizard"

    file = fields.Binary('File')
    file_import_type = fields.Selection(
        [('csv', 'CSV File'),
         ('xls', 'XLS File')],
        string='Select',
        default='csv'
    )
    option_import_file_by = fields.Selection(
        [('barcode', 'Barcode'),
         ('code', 'Code'),
         ('name', 'Name')],
        string='Import Product By',
        default='code'
    )
    is_validate_inventory = fields.Boolean(string="Validate Inventory")
    lot_option = fields.Boolean(string="Import Serial/Lot number with Expiry Date")
    location_id_option = fields.Boolean(string="Allow to Import Location on inventory line from file")

    def create_inventory_move(self, val, product_uom_id, stock_location_id):
        """Create a stock move for inventory adjustment."""
        stock_move_obj = self.env['stock.move']

        # Definir la ubicación de destino (ubicación interna de inventario)
        adjust_location = self.env['stock.location'].search([('name', '=', 'Inventory adjustment')], limit=1)
        # Crear un nuevo movimiento de inventario
        new_move = stock_move_obj.create({
            'name': _('Inventory Adjustment'),
            'product_id': val['product'],  # ID del producto
            'product_uom_qty': float(val['quantity']),  # Cantidad de producto
            'product_uom': product_uom_id.id,  # Unidad de medida
            'location_id': adjust_location.id,  # Ubicación de origen: Ajuste de inventario
            'location_dest_id': stock_location_id.id,  # Ubicación de destino: Ubicación real de inventario
            'state': 'draft',  # Estado inicial del movimiento
            'date': val['date'],  # Fecha del movimiento
            'company_id': self.env.company.id  # Compañía
        })

        

        # Crear una línea de movimiento de inventario asociada al movimiento creado
        try:
            stock_move_line_obj = self.env['stock.move.line'].create({
                'move_id': new_move.id,  # ID del stock.move asociado
                'product_id': val['product'],  # ID del producto
                'product_uom_id': product_uom_id.id,  # Unidad de medida
                'location_id': adjust_location.id,  # Ubicación de origen
                'location_dest_id': stock_location_id.id,  # Ubicación de destino
                'qty_done': float(val['quantity']),  # Cantidad completada
                'date': val['date'],  # Fecha del movimiento
                'state': 'draft',  # Estado del movimiento
                'company_id': self.env.company.id,  # Compañía
            })
            new_move._action_confirm()
            new_move._action_assign()
            new_move._action_done()
            _logger.info(f'Inventory move created for product {val.get("product")} estatus: {new_move.state}')
        except Exception as e:
            _logger.error(f"Error creating inventory move for product {val.get('product')}:{e} estatus: {new_move.state}")
        # Confirmar y validar el movimiento de inventario
        # new_move._action_confirm()
        # new_move._action_done()

        return new_move

    ############################### Implementacion foresdbs ########################################

    def create_new_stock_line(self, val, product_uom_id, stock_location_id):
        """Create a new stock line for the given product, UoM, and location."""
        stock_quant_obj = self.env['stock.quant']

        # Crear el diccionario de valores para el nuevo registro
        new_stock_line = {
            'product_id': val['product'],
            'location_id': stock_location_id.id,
            'quantity': float(val['quantity']),
            'product_uom_id': product_uom_id.id,
            'inventory_date': val['date'],
            'in_date': val['date'],
            'import_data': True,
        }


        # Si la opción de lotes está habilitada, agregar el lote a los valores
        if self.lot_option and 'lot' in val:
            lot_id = self.env['stock.production.lot'].search([('name', '=', val['lot']), ('product_id', '=', val['product'])], limit=1)
            if not lot_id:
                lot_id = self.env['stock.production.lot'].create({
                    'name': val['lot'],
                    'product_id': val['product'],
                    'company_id': self.env.company.id,
                })
            new_stock_line['lot_id'] = lot_id.id

        # Crear la nueva línea de inventario
        try:
            stock_quant_obj.create(new_stock_line)
        except Exception as e:
            raise ValidationError(_('Error creating new stock line: %s') % e)


    def update_product_values(self, val):
        """Update product values based on input data."""
        
        # Obtén el producto basado en el ID proporcionado en val
        product = self.env['product.product'].browse(val['product'])

        # Verifica si el producto existe
        if not product:
            raise ValidationError(_('Product with ID %s not found.') % val['product'])

        # Actualiza los valores del producto si es necesario
        # Por ejemplo, puedes actualizar el campo 'quantity' en el producto (aunque generalmente este campo no se actualiza así en Odoo)
        # Dependiendo del contexto, puede que quieras actualizar otros campos específicos del producto

        # Aquí solo retorno el producto, ya que la lógica de actualización de cantidad suele manejarse en otros lugares
        return product
    
    def get_product_uom(self, val):
        """Get the product unit of measure (UoM) based on the product ID."""
        
        # Obtén el ID del producto desde val
        product_id = val.get('product')
        
        # Verifica si se proporciona el ID del producto
        if not product_id:
            raise ValidationError(_('No product ID provided in the input data.'))
        
        # Busca el registro del producto usando el ID proporcionado
        product = self.env['product.product'].browse(product_id)

        # Verifica si el producto existe
        if not product.exists():
            raise ValidationError(_('Product with ID %s not found.') % product_id)
        
        # Obtén la unidad de medida (UoM) del producto
        product_uom_id = product.uom_id

        # Verifica si la UoM del producto es válida
        if not product_uom_id:
            raise ValidationError(_('Unit of measure (UoM) for product ID %s not found.') % product_id)

        # Retorna el objeto del modelo 'uom.uom' y la unidad de medida del producto
        return self.env['uom.uom'], product_uom_id
    
    def update_stock_line_without_lot(self, val, product_id, product_uom_id, stock_location_id, generate_inv, counter_product):
        """Update stock line without lot information."""
        
        # Busca la línea de inventario existente basada en el producto y la ubicación
        search_line = self.env['stock.quant'].search([
            ('product_id', '=', val['product']),
            ('location_id', '=', stock_location_id.id),
            ('inventory_date', '=', val['date']),
            ('in_date','=', val['date'])
        ], limit=1)

        # Si se encuentra la línea, actualiza la cantidad de inventario
        if search_line:
            self.update_existing_stock_line(search_line, val)
        else:
            self.create_inventory_move(val, product_uom_id, stock_location_id)
            # self.create_new_stock_line(val, product_uom_id, stock_location_id)
            

        # Devuelve los valores actualizados
        return 1, counter_product, generate_inv.id if generate_inv else None

    def update_existing_stock_line(self, search_line, val):
        """Update an existing stock line with new values."""
        
        # Actualiza la cantidad de inventario en la línea existente
        update_values = {
            'quantity': float(val['quantity'])
        }

        # Si la opción de lotes está habilitada, actualiza el lote en la línea de inventario
        if self.lot_option and 'lot' in val:
            lot_id = self.env['stock.production.lot'].search([
                ('name', '=', val['lot']), 
                ('product_id', '=', val['product'])
            ], limit=1)
            if not lot_id:
                lot_id = self.env['stock.production.lot'].create({
                    'name': val['lot'],
                    'product_id': val['product'],
                    'company_id': self.env.company.id,
                })
            update_values['lot_id'] = lot_id.id

        # Usa el método write() para guardar los cambios en la línea de inventario
        search_line.sudo().write(update_values)
        


                
        
        



    
    def get_success_response(self, flag, g_inv_id):
        """Generar una respuesta de éxito después de importar los datos de inventario."""
        
        # Mensaje de éxito genérico
        message = _("The inventory data has been successfully imported.")
        
        # Verifica si hay algún flag o identificador de inventario generado
        if g_inv_id:
            message += _(" Generated Inventory ID: %s") % g_inv_id

        # Regresar un mensaje de éxito o una acción
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': message,
                'type': 'success',
                'sticky': False,  # Este campo determina si la notificación se cierra automáticamente
            }
        }

    def import_excel(self):
        """Import inventory data from an Excel file."""
        if not self.file:
            raise ValidationError(_('Please upload a file to import.'))

        # Decodifica el archivo y lee su contenido
        data = base64.b64decode(self.file)
        try:
            workbook = xlrd.open_workbook(file_contents=data)
        except xlrd.biffh.XLRDError:
            raise ValidationError(_('Invalid Excel file! Please check the file format.'))

        # Selecciona la primera hoja de trabajo
        sheet = workbook.sheet_by_index(0)
        
        # Extrae las cabeceras de la primera fila
        keys = [sheet.cell(0, col_index).value for col_index in range(sheet.ncols)]
        if self.lot_option:
            keys.append('lot')

        flag = 0
        generate_inv = self.env['gen.inventory']
        counter_product = 0.0
        g_inv_id = None

        # Recorre cada fila del archivo (saltando la primera fila de encabezados)
        for row_idx in range(1, sheet.nrows):
            row = [sheet.cell(row_idx, col_index).value for col_index in range(sheet.ncols)]
            val = self.process_csv_line(keys, row, self.env['product.product'], self.env['stock.quant'], generate_inv=generate_inv, flag=flag, counter_product=counter_product, g_inv_id=g_inv_id)
            flag, counter_product, g_inv_id = self.update_inventory_values(flag, val, generate_inv, counter_product)

        return self.get_success_response(flag, g_inv_id)



    #######################################################################

    def import_inventory_file(self):
        self.validate_file()

        if self.file_import_type == 'csv':
            return self.import_csv()
        elif self.file_import_type == 'xls':
            return self.import_excel()
        else:
            raise ValidationError("Invalid File Type...Supported Types:'csv',''excel'.")

    def validate_file(self):
        if not self.file:
            raise ValidationError(_('Select File!'))

    def import_csv(self):
        """Import inventory data from a CSV file."""
        data = base64.b64decode(self.file)
        try:
            io.StringIO(data.decode("utf-8"))
        except UnicodeError:
            raise ValidationError('File is not valid!')

        keys = self.get_csv_keys()
        inventory_obj = self.env['stock.quant']
        product_obj = self.env['product.product']
        csv_data = base64.b64decode(self.file)
        data_file = io.StringIO(csv_data.decode("utf-8"))
        data_file.seek(0)
        file_reader = list(csv.reader(data_file, delimiter=','))
        flag = 0
        generate_inv = self.env['gen.inventory']
        counter_product = 0.0
        g_inv_id = None

        # try:
        file_reader = file_reader[1:]
        for i, field in enumerate(file_reader, start=1):
            val = self.process_csv_line(keys, field, product_obj, inventory_obj, generate_inv=generate_inv, flag=flag, counter_product=counter_product, g_inv_id=g_inv_id)
            flag, counter_product, g_inv_id = self.update_inventory_values(flag, val, generate_inv, counter_product)
        # except Exception:
        #     raise exceptions.ValidationError(_("Invalid File!"))

        return self.get_success_response(flag, g_inv_id)

    def get_csv_keys(self):
        keys = ['location', 'code', 'quantity', 'date', 'uom']
        if self.lot_option:
            keys.append('lot')
        return keys

    def process_csv_line(self, keys, field, product_obj, inventory_obj, **kwargs):
        """Process a line from the CSV file and update stock information."""
        values = dict(zip(keys, field))
        val = {}
        prod_lst = self.find_product(values['code'], product_obj)
        stock_location_id = self.find_stock_location(values['location'])
        generate_inv = kwargs.get('generate_inv')
        flag = kwargs.get('flag', 0)
        counter_product = kwargs.get('counter_product', 0.0)
        g_inv_id = kwargs.get('g_inv_id')

        if prod_lst:
            val['product'] = prod_lst[0].id
            val['quantity'] = values['quantity']
        
        if stock_location_id:
            val['location'] = stock_location_id.complete_name
        else:
            raise ValidationError(_('Location Not Found  "%s"') % values.get('location'))

        if values.get('date'):
            val['date'] = self.check_date(values.get('date'))
        else:
            raise ValidationError(_('Please add date field on sheet.'))
        
        if bool(val):
            product_id = product_obj.browse(val['product'])
            product_uom_obj = self.env['uom.uom']
            user_lang = self.env.context.get('lang')
            product_uom_id = product_uom_obj.search([('name', '=', values['uom'])])
            # if self.lot_option:
            #     search_line = self.env['stock.quant'].search([
            #         ('product_id', '=', val['product']),
            #         ('location_id', '=', stock_location_id.id),
            #         ('lot_id.name', '=', values['lot'])
            #     ])

            #     if search_line:
            #         self.update_existing_stock_line(search_line, val)
            #     else:
            #         self.create_new_stock_line(val, product_uom_id, stock_location_id)

            #     flag, counter_product, g_inv_id = self.update_inventory_values(flag, val, generate_inv, counter_product)
            # else:
            #     search_line = self.env['stock.quant'].search([
            #         ('product_id', '=', val['product']),
            #         ('location_id', '=', stock_location_id.id)
            #     ])

            #     if search_line:
            #         self.update_existing_stock_line(search_line, val)
            #     else:
            #         self.create_new_stock_line(val, product_uom_id, stock_location_id)

            #     flag, counter_product, g_inv_id = self.update_inventory_values(flag, val, generate_inv, counter_product)
        else:
            raise ValidationError(_('Product Not Found  "%s"') % values.get('code'))

        return val

    def find_product(self, code, product_obj):
        """Find Products"""
        if self.option_import_file_by == 'barcode':
            return product_obj.search([('barcode', '=', code)])
        elif self.option_import_file_by == 'code':
            return product_obj.search([('default_code', '=', code)])
        else:
            return product_obj.search([('name', '=', code)])

    def find_stock_location(self, location):
        """Find a stock location by its complete name."""
        stock_location_id = self.env['stock.location'].search([('complete_name', '=', location)])
        if not stock_location_id:
            raise ValidationError(_('"%s" Location is not available.') % location)
        return stock_location_id

    def update_inventory_values(self, flag, val, generate_inv, counter_product):
        if bool(val):
            flag, counter_product, g_inv_id = self.update_stock_line(val, generate_inv, counter_product)
        return flag, counter_product, g_inv_id

    def update_stock_line(self, val, generate_inv, counter_product):
        """Update stock line based on input values."""
        product_id = self.update_product_values(val)
        product_uom_obj, product_uom_id = self.get_product_uom(val)
        stock_location_id = self.find_stock_location(val['location'])

        if self.lot_option:
            return self.update_stock_line_with_lot(val, product_id, product_uom_id, stock_location_id, generate_inv,
                                                   counter_product)
        else:
            return self.update_stock_line_without_lot(val, product_id, product_uom_id, stock_location_id, generate_inv,
                                                      counter_product)

    def update_stock_line_with_lot(self, val, product_id, product_uom_id, stock_location_id, generate_inv,
                                   counter_product):
        """Update stock line with lot information."""
        search_line = self.env['stock.quant'].search([
            ('product_id', '=', val['product']),
            ('location_id', '=', stock_location_id.id),
            ('lot_id.name', '=', val['lot']),
            ('in_date', '=', val['date']),
            ('inventory_date', '=', val['date'])
        ])

        if search_line:
            self.update_existing_stock_line(search_line, val)
        else:
            self.create_new_stock_line(val, product_uom_id, stock_location_id)

    def check_date(self, date):
        """Check if the provided date has the correct format (YYYY-MM-DD)."""
        if date:
            try:
                valid_date = datetime.strptime(str(date), "%Y-%m-%d").date()
            except Exception:
                raise ValidationError(_('Date format should be YYYY-MM-DD.'))
            return valid_date
        else:
            raise ValidationError(_('Please add date field on sheet.'))
