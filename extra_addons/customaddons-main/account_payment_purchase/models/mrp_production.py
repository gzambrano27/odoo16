from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import ValidationError
import xlsxwriter
import base64
from io import BytesIO
from datetime import datetime
import pytz

class mrp_bom(models.Model):
    _inherit = 'mrp.bom'

    #inter_transfer = fields.Boolean('Es lista para transferencia')
    total_cost = fields.Float("Total", compute="_calc_total", digits=dp.get_precision('Product Unit of Measure'))
    
    @api.depends('bom_line_ids.subtotal')
    def _calc_total(self):
        for move in self:
            tot =0
            for line in move.bom_line_ids:
                tot = tot + line.subtotal      
            move.total_cost = tot

class MrpBomLineInherit(models.Model):
    _inherit = 'mrp.bom.line'

    referencia_anterior = fields.Char(related = 'product_id.referencia_anterior', string='Referencia Anterior')
    default_code = fields.Char(related = 'product_id.default_code' , string='Referencia Interna')
    cost = fields.Float("Costo", compute="_calc_costo", digits=dp.get_precision('Product Unit of Measure'))
    subtotal = fields.Float("Subtotal", compute="_calc_subtotal", digits=dp.get_precision('Product Unit of Measure'))
    
    
    @api.depends('product_qty', 'product_id')
    def _calc_costo(self):
        for move in self:
            move.cost = self.env['product.product'].browse(move.product_id.id).standard_price
    
    @api.depends('product_qty', 'product_id','cost')
    def _calc_subtotal(self):
        for move in self:
            move.subtotal = move.product_qty*move.cost

class StockMove(models.Model):
    _inherit = 'stock.move'

    referencia_anterior = fields.Char(related = 'product_id.referencia_anterior', string='Referencia Anterior')
    default_code = fields.Char(related = 'product_id.default_code' , string='Referencia Interna')
    cost = fields.Float("Costo", compute="_calc_costo", digits=dp.get_precision('Product Unit of Measure'))
    subtotal = fields.Float("Subtotal", compute="_calc_subtotal", digits=dp.get_precision('Product Unit of Measure'))

    @api.depends('product_uom_qty', 'product_id')
    def _calc_costo(self):
        for move in self:
            move.cost = self.env['product.product'].browse(move.product_id.id).standard_price
    
    @api.depends('product_uom_qty', 'product_id','cost')
    def _calc_subtotal(self):
        for move in self:
            move.subtotal = move.product_uom_qty*move.cost

    @api.model
    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id, svl_id, description):
        # Obtenemos el producto del movimiento de stock
        product = self.product_id

        # Verificar si el movimiento está relacionado con una orden de producción
        if self.raw_material_production_id or self.production_id:
            # Verificamos si el nombre del producto es "consumible"
            print(self.bom_line_id.bom_id.product_tmpl_id.name)
            if self.bom_line_id.bom_id.product_tmpl_id.name == 'CONSUMIBLE':
                # Obtener las cuentas contables de la categoría del producto
                debit_account_id = product.categ_id.property_stock_account_input_categ_id_consumible.id or debit_account_id
                credit_account_id = product.categ_id.property_stock_account_output_categ_id_consumible.id or credit_account_id
            if self.bom_line_id.bom_id.product_tmpl_id.name == 'SUMINISTROS PRODUCCION':
                # Obtener las cuentas contables de la categoría del producto
                debit_account_id = product.categ_id.property_stock_account_input_categ_id_suministro.id or debit_account_id
                credit_account_id = product.categ_id.property_stock_account_output_categ_id_suministro.id or credit_account_id 

        # Llamar al método original con los parámetros completos
        return super(StockMove, self)._prepare_account_move_line(
            qty, cost, credit_account_id, debit_account_id, svl_id, description
        )

class mrp_production(models.Model):
    _inherit = 'mrp.production'

    total_cost = fields.Float("Total", compute="_calc_total", digits=dp.get_precision('Product Unit of Measure'))
    production_type = fields.Selection([
        ('consumible', 'Consumible'),
        ('normal', 'Normal')
    ], string="Tipo Produccion", default='normal')
    
    @api.model
    def create(self, vals):
        product_id = vals.get('product_id')
        product = self.env['product.product'].browse(product_id)
        # Comprobar el tipo de orden de producción y asignar la secuencia correspondiente
        if vals.get('production_type') == 'consumible':
            # Validar que el producto sea de tipo consumible
            if product and product.detailed_type != 'consu':
                raise ValidationError("El producto seleccionado debe ser de tipo 'Consumible' para esta orden de producción.")
            vals['name'] = self.env['ir.sequence'].next_by_code('mrp.production.order.consumible') or '/'
        else:
            if product and product.detailed_type == 'consu':
                raise ValidationError("La produccion que estas realizando noo aplica para esta orden de producción.")
        return super(mrp_production, self).create(vals)

    @api.depends('move_raw_ids.subtotal')
    def _calc_total(self):
        for move in self:
            tot =0
            for line in move.move_raw_ids:
                tot = tot + line.subtotal      
            move.total_cost = tot

    def generate_excel_and_send_email_mo(self):
        # Crear un archivo Excel en memoria
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Reporte')
        currency_format = workbook.add_format({'num_format': '$#,##0.00'})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        sql_mo = """
            select s.date,
                    p.state,
                    p.name,
                    p.origin,
                    (select x.default_code from product_product x where x.id = p.product_id)cod_prod_term,
                    (select name->>'es_EC' from product_template pt where pt.id = (select x.product_tmpl_id from product_product x where x.id = p.product_id))producto_terminado,
                    p.product_qty cantproducido,
                    (select x.default_code from product_product x where x.id = s.product_id)cod_prod_material,
                    (select name->>'es_EC' from product_template pt where pt.id = (select x.product_tmpl_id from product_product x where x.id = s.product_id))producto_material,
                    s.product_qty cant,
                    s.price_unit,
                    s.product_qty,
                    (s.price_unit * s.product_qty)costo_unit_MRP
                    
                    from
                    mrp_production p,
                    stock_move s
                    where p.name = s.origin
                    and p.name like '%MO/%'
                    and s.product_qty > 0
                    order by 3
        """
        self.env.cr.execute(sql_mo)
        # Escribir algunos datos de ejemplo
        worksheet.write('A1', 'Fecha')
        worksheet.write('B1', 'Estado')
        worksheet.write('C1', 'Orden Produccion')
        worksheet.write('D1', 'Origen')
        worksheet.write('E1', 'Cod Prod Terminado')
        worksheet.write('F1', 'Producto Terminado')
        worksheet.write('G1', 'Cantidad Producida')
        worksheet.write('H1', 'Cod Material')
        worksheet.write('I1', 'Material')
        worksheet.write('J1', 'Cantidad')
        worksheet.write('K1', 'Precio Unitario')
        worksheet.write('L1', 'Cantidad Producto')
        worksheet.write('M1', 'Costo Unit')
        
        
        row = 1
        # Lee y recorre los resultados
        results = self.env.cr.fetchall()
        for x in results:
            # Aquí puedes acceder a cada columna de la fila, por ejemplo:
            worksheet.write(row, 0, x[0], date_format)
            worksheet.write(row, 1, x[1])
            worksheet.write(row, 2, x[2])
            worksheet.write(row, 3, x[3])
            worksheet.write(row, 4, x[4])
            worksheet.write(row, 5, x[5])
            worksheet.write(row, 6, x[6])
            worksheet.write(row, 7, x[7])
            worksheet.write(row, 8, x[8])
            worksheet.write(row, 9, x[9])
            worksheet.write(row, 10, x[10], currency_format)
            worksheet.write(row, 11, x[11])
            worksheet.write(row, 12, x[12], currency_format)
            row += 1

        workbook.close()
        output.seek(0)
        excel_data = output.read()
        output.close()

        # Codificar el archivo en base64
        excel_base64 = base64.b64encode(excel_data)

        # Crear un adjunto para el correo
        attachment = self.env['ir.attachment'].create({
            'name': 'ReporteMO.xlsx',
            'type': 'binary',
            'datas': excel_base64,
            'store_fname': 'ReporteMO.xlsx',
            'res_model': 'excel.report.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        # Enviar el correo
        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)
        
        # Obtener la fecha y hora actual en UTC y convertirla a la zona horaria local
        current_datetime = fields.Datetime.now()
        current_datetime_local = pytz.utc.localize(current_datetime).astimezone(local_tz)
        mail_values = {
            'subject': f'ACTUALIZACIÓN DATOS OP ODOO {current_datetime_local}',
            'body_html': '<p>Adjunto encontrarás el reporte de OP en formato Excel.</p>',
            'email_to': 'mmorquecho@gpsgroup.com.ec',#,mmorquecho
            'attachment_ids': [(6, 0, [attachment.id])],
        }
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Correo Enviado',
                'message': 'El reporte en Excel ha sido enviado correctamente.',
                'type': 'success',
                'sticky': False,
            }
        }