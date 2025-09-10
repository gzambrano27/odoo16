# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import date_utils
import io
import xlsxwriter
from odoo.http import content_disposition, request
import base64
import datetime


class PurchaseProductPeriodReport(models.TransientModel):
    _name = 'purchase.product.period.report'
    _description = 'Reporte de productos por Órdenes de Compra'

    company_ids = fields.Many2many(
        'res.company',
        string="Compañías",
        default=lambda self: self.env.company,
        domain=lambda self: [('id', 'in', self.env.user.company_ids.ids)]
    )

    # purchase_order_type = fields.Selection(
    # [('service', 'Servicio'), ('product', 'Producto'), ('mixed', 'Producto y Servicio')],
    # string="Tipo de Orden de Compra",
    # required=False,
    # default='product'
    # )

    detailed_type = fields.Selection(
        [('consu', 'Consumible'), ('service', 'Servicio'), ('product', 'Almacenable')],
        string="Tipo de Producto",
        required=True,
        default='product'
    )

    start_date = fields.Date(
        string="Fecha Inicio",
        required=True,
        default=fields.Date.today
    )
    end_date = fields.Date(
        string="Fecha Fin",
        required=True,
        default=fields.Date.today
    )

    def generate_xlsx_report(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Producto O/C')

        # Definir formato de encabezado
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})
        data_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd','border': 1})  # Formato de fecha en Excel

        # Encabezados
        headers = [
            'Empresa', 'SKU', 'Descripción ', 'Unidades Recibidas', 'Fecha de Efectiva'
        ]

        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)

        company_ids = tuple(self.company_ids.ids) if self.company_ids else (self.env.company.id,)
        # purchase_order_type = self.purchase_order_type
        detailed_type = self.detailed_type

        query = """
        SELECT 
            rc.name AS company_name, 
            pp.default_code AS sku,
            pt.name->>'es_EC' as Descripcion,
            CAST(pol.qty_received AS DECIMAL(10,0)) AS unidades_compra_recib,
            po.effective_date as fech
        
        FROM purchase_order AS po
        INNER JOIN purchase_order_line AS pol ON po.id = pol.order_id 
        INNER JOIN product_product AS pp ON pp.id = pol.product_id 
        INNER JOIN product_template AS pt ON pt.id = pp.product_tmpl_id 
        LEFT JOIN res_company AS rc ON po.company_id = rc.id 
        WHERE 
            po.state IN ('purchase') 
            /* AND pol.qty_received > 0 */
            AND po.company_id IN %s  
            AND pt.detailed_type = %s
            AND po.effective_date between %s and %s
        GROUP BY 
            rc.name, 
            po.state, 
            po.name, 
            pp.default_code, 
            pp.id, 
            pol.qty_received, 
            po.create_date, 
            po.effective_date, 
            pt.name->>'es_EC', 
            po.company_id
        ORDER BY 
            po.company_id, 
            pp.default_code, 
            po.effective_date;
        """

        #self.env.cr.execute(query, (company_ids, purchase_order_type, self.start_date, self.end_date,))
        self.env.cr.execute(query, (company_ids, detailed_type, self.start_date, self.end_date,))
        records = self.env.cr.fetchall()


        # Insertar datos en el archivo Excel
        for row_num, record in enumerate(records, start=1):
            for col_num, value in enumerate(record):
                if isinstance(value, datetime.datetime) or isinstance(value, datetime.date):
                    sheet.write_datetime(row_num, col_num, value, date_format)  # Escribir correctamente la fecha
                else:
                    sheet.write(row_num, col_num, value, data_format)

        workbook.close()
        output.seek(0)
        return output.read(), 'xlsx', 'Reporte_Product_period.xlsx'
        #return output.read(), 'xlsx', 'Reporte_OC_Tránsito.xlsx'

    def action_export_xlsx(self):
        data, file_format, file_name = self.generate_xlsx_report()

        # Crear un adjunto con el archivo generado
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': base64.b64encode(data),  # Codificar en base64
            'store_fname': file_name,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'purchase.product.period.report',
            'res_id': self.id,
        })

        # Devolver la acción para descargar el archivo
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % attachment.id,
            'target': 'self',
        }

