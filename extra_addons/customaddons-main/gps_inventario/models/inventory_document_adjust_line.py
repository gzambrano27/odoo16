# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _,SUPERUSER_ID
import base64
import xlsxwriter
import io

class InventoryDocumentAdjustLine(models.Model):
    _name="inventory.document.adjust.line"
    _description="Ajuste de Documento de Inventario"
    
    document_id=fields.Many2one("inventory.document.adjust","Ajuste",ondelete="cascade")
    stock_location_id = fields.Many2one("stock.location", string="Ubicacion", required=True)

    company_id=fields.Many2one(related="stock_location_id.company_id",store=False,readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)

    name=fields.Char("Descripcion",required=True)
    product_id=fields.Many2one("product.product","Producto",domain=[('detailed_type','=','product')])
    stock=fields.Float("Stock Sistema",default=0)
    quantity=fields.Float("Stock",default=0)
    adjust=fields.Float("Ajuste",default=0,compute="_compute_adjust",store=True)
    apply=fields.Boolean("Aplicar",default=False)
    force_apply=fields.Boolean("Forzar Aplicar",default=False)
    comments=fields.Text("Observaciones")
    origin=fields.Selection([('original','Original del Inventario'),('manual','Ingresado Manualmente')],string="Origen",default="original")

    parent_state=fields.Selection(related="document_id.state",store=False,readonly=True)

    standard_price=fields.Float(compute="_get_standard_price",readonly=True,store=True,string="Costo")
    total_cost=fields.Monetary(compute="_get_total_cost",readonly=True,store=True,string="Total Costo")

    referencia_anterior = fields.Char(compute="_get_standard_price",store=False,readonly=True, string='Referencia Anterior')
    file_data = fields.Binary(string="Archivo Excel", readonly=True)

    @api.depends('product_id')
    def _get_standard_price(self):
        for brw_each in self:
            brw_each.referencia_anterior = brw_each.product_id.referencia_anterior
            brw_each.standard_price=brw_each.product_id.standard_price

    @api.depends('standard_price','adjust')
    @api.onchange('standard_price','adjust')
    def _get_total_cost(self):
        for brw_each in self:
            brw_each.total_cost = brw_each.adjust *brw_each.standard_price

    _order="stock_location_id asc,product_id asc"

    @api.onchange('quantity','stock')
    def _compute_adjust(self):
        for brw_each in self:
            adjust=brw_each.quantity-brw_each.stock           
            brw_each.adjust=adjust
    
    def update_stock(self):
        sup=self.env["res.users"].browse(SUPERUSER_ID)
        OBJ_QUANT=self.env["stock.quant"].sudo().with_user(sup)
        self.ensure_one()
        brw_line=self
        brw_product=brw_line.product_id
        stock_location_id=brw_line.stock_location_id and brw_line.stock_location_id.id or  brw_line.document_id.stock_location_id.id
        brw_product=brw_product.with_context({"lot_id":stock_location_id,"owner_id":None,"package_id":None, "from_date":False, "to_date":False})
        stock=0
        if stock_location_id:
            srch_quant=OBJ_QUANT.search([('product_id','=',brw_line.product_id.id),('location_id','=',stock_location_id)])
            if srch_quant:
                stock=srch_quant[0].quantity
        brw_line.stock=stock
        brw_line._compute_adjust()
        
    @api.onchange('comments')
    def onchange_comments(self):
        self.comments=self.comments and self.comments.upper() or  None
        
    @api.onchange('apply')
    def onchange_apply(self):
        self.force_apply=self.apply

    def generate_adjustment_lines(self):
        if not self:
            raise ValidationError(_("Por favor, seleccione al menos un registro."))

        # Crear el archivo Excel en memoria
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet('Adjustments')

        # Formatos
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        header_format = workbook.add_format({'bold': True, 'align': 'left'})
        value_format = workbook.add_format({'align': 'left'})

        # Cabecera principal
        #sheet.merge_range('A1:D1', record.company_id.name, title_format)
        sheet.write('A1', self.document_id.company_id.name, title_format)
        #sheet.merge_range('E1:H1', 'AJUSTE DE INVENTARIO', title_format)
        sheet.write('G1', 'AJUSTE DE INVENTARIO', title_format)

        # Detalles de la cabecera
        sheet.write('A2', 'FECHA DE INVENTARIO:', header_format)
        sheet.write('B2', str(self.document_id.date_from), value_format)

        sheet.write('A3', 'PRODUCTOS:', header_format)
        product_names = ','.join(self.document_id.product_ids.mapped('display_name'))
        #sheet.merge_range('B3:H3', product_names, value_format)
        sheet.write('B3', product_names, value_format)

        sheet.write('A4', 'UBICACION:', header_format)
        sheet.write('B4', self.document_id.stock_location_id.display_name, value_format)

        sheet.write('E2', '# LINEAS:', header_format)
        sheet.write('F2', len(self.document_id.line_ids), value_format)

        sheet.write('E3', 'RESPONSABLES:', header_format)
        user_names = ','.join(self.document_id.user_ids.mapped('name'))
        #sheet.merge_range('F3:H3', user_names, value_format)
        sheet.write('F3', user_names, value_format)
        # Espaciado para la tabla
        row = 4

        # Encabezados dinámicos según grupo de usuario
        if self.env.user.has_group('gps_inventario.group_ajuste_inventario_manager') or self.env.user.has_group('gps_inventario.group_ajuste_inventario_costo_manager'):
            headers = ['#ID', 'Ubicación', 'Ref. Anterior', 'Ref. Interna', 'Nombre', 'Cantidad', 'Comentario', 'Unidad Medida', 'Stock', 'Costo']
        else:
            headers = ['#ID', 'Ubicación', 'Ref. Anterior', 'Ref. Interna', 'Nombre', 'Cantidad', 'Comentario', 'Unidad Medida']

        # Escribir encabezados
        for col, header in enumerate(headers):
                sheet.write(row, col, header, header_format)
        # Escribir datos de los registros seleccionados
        row = row + 1
        for record in self:
            sheet.write(row, 0, record.id)
            sheet.write(row, 1, record.stock_location_id.display_name or '')
            sheet.write(row, 2, record.product_id.referencia_anterior or '')
            sheet.write(row, 3, record.product_id.default_code or '')
            sheet.write(row, 4, record.product_id.name or '')
            sheet.write(row, 5, 0)
            sheet.write(row, 6, '')
            sheet.write(row, 7, record.product_id.uom_id.name or '')
            if self.env.user.has_group('gps_inventario.group_ajuste_inventario_manager') or self.env.user.has_group('gps_inventario.group_ajuste_inventario_costo_manager'):
                sheet.write(row, 8, record.stock or 0)
                sheet.write(row, 9, record.standard_price or 0)
            row += 1

        # Guardar el archivo en memoria
        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()
        # Crear un adjunto temporal para descargar
        attachment = self.env['ir.attachment'].create({
            'name': 'Ajuste_de_Inventario.xlsx',
            'type': 'binary',
            'datas': file_data,
            'store_fname': 'Ajuste_de_Inventario.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # Guardar el ID del adjunto para su eliminación
        attachment_id = attachment.id

        # Generar URL de descarga
        download_url = f'/web/content/{attachment_id}?download=true'

        # Retornar acción para descargar el archivo
        return {
            'type': 'ir.actions.act_url',
            'url': download_url,
            'target': 'self',
        }