from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import io
import xlrd
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)

class ImportOC(models.TransientModel):
    _name = 'import.oc'
    _description = 'Import OC'

    file = fields.Binary(string="File", required=True)
    import_date = fields.Datetime(string="Import Date", default=datetime.now())
    currency_id = fields.Many2one('res.currency', string="Currency", required=True)
    payment_term_id = fields.Many2one('account.payment.term', string="Payment Term", required=True)
    planeed_date = fields.Date(string="Planeed Date", default=datetime.now())

    
    def import_oc(self):
      try:
          # Decodificar y abrir el archivo Excel
          data = base64.b64decode(self.file)
          book = xlrd.open_workbook(file_contents=io.BytesIO(data).read())
          sheet = book.sheet_by_index(0)

          # Leer la cabecera de la orden de compra
          header = sheet.row_values(1)
          supplier_name = header[0]
          raw_deadline = header[1]
          payment_term = header[2]
          currency_name = header[3]

          # Buscar o crear el proveedor
          supplier = self.env['res.partner'].search([('name', '=', supplier_name)], limit=1)
          if not supplier:
              supplier = self.env['res.partner'].create({'name': supplier_name})


          # Crear la orden de compra
          po = self.env['purchase.order'].create({
              'partner_id': supplier.id,
              'date_order': self.import_date,
              'currency_id': self.currency_id.id,
              'solicitante': self.env.user.id,
              'company_id': self.env.company.id,
              'state': 'draft',
              'payment_term_id': self.payment_term_id.id,
              'imported_oc': True,
          })

          # Recorrer cada fila del archivo, comenzando desde la segunda fila para los productos
          for i in range(1, sheet.nrows):
              row = sheet.row_values(i)
              
              # Obtener los detalles del producto
              product_code = row[4]
              product_name = row[5]
              product_description = row[6]
              product_quantity = row[7]
              product_uom = row[8]
              product_price =   row[9]
              
              # Verificar si el producto ya existe
              product = self.env['product.product'].search([('referencia_anterior', '=', product_code)], limit=1)
              if not product:
                  # Crear producto si no existe
                  secuencia = self.env['ir.sequence'].next_by_code('product.internal.ref')
                  product = self.env['product.product'].create({
                      'name': product_name,
                      'referencia_anterior': product_code,
                      'description': product_description,
                      'uom_id': self.env['uom.uom'].search([('name', '=', product_uom)], limit=1).id,
                      # 'list_price': product_price,
                      'default_code': secuencia,
                      'imported_product': True
                  })

              # Agregar la línea de productos a la orden de compra
              self.env['purchase.order.line'].create({
                  'order_id': po.id,
                  'product_id': product.id,
                  'product_qty': product_quantity,
                  'price_unit': product_price,
                  'product_uom': product.uom_id.id
              })

          _logger.info('Órdenes de compra creadas exitosamente.')
          return {'type': 'ir.actions.act_window_close'}
      except Exception as e:
          raise UserError(e)
      return True
