# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import date_utils
import io
import xlsxwriter
from odoo.http import content_disposition, request
import base64
import datetime


class PurchaseTransitInventoryReport(models.TransientModel):
    _name = 'purchase.transit.inventory.report'
    _description = 'Reporte de Órdenes de Compra en Tránsito'

    company_ids = fields.Many2many(
        'res.company',
        string="Compañías",
        default=lambda self: self.env.company,
        domain=lambda self: [('id', 'in', self.env.user.company_ids.ids)]
    )

    purchase_order_type = fields.Selection(
        [('service', 'Servicio'), ('product', 'Producto'), ('mixed', 'Producto y Servicio')],
        string="Tipo de Orden de Compra",
        required=True,
        default='service'
    )

    def generate_xlsx_report(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('OC en Tránsito')

        # Definir formato de encabezado
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})
        data_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd','border': 1})  # Formato de fecha en Excel

        # Encabezados
        headers = [
            'Empresa', 'Estado', 'RUC', 'Proveedor', 'Orden de Compra', 'Fecha Creación', 'Fecha Aprobación',
            'Referencia Producto', 'Nombre Producto', 'Tiempo de Entrega', 'Cantidad Ordenada', 'Cantidad Recibida',
            'Cantidad Faltante', 'Precio Unitario', 'Costo Faltante', 'Fecha Planificada', 'Cuentas Analíticas',
            'Tipo de Orden', 'Creado Por', 'Aprobado Por', 'Fecha Efectiva'
        ]

        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)

        company_ids = tuple(self.company_ids.ids) if self.company_ids else (self.env.company.id,)
        purchase_order_type = self.purchase_order_type


        query = """
        SELECT 
            rc.name AS company_name, po.state, rp.vat, rp.name AS partner_name, po.name AS purchase_order,
            po.create_date, po.date_approve, pp.default_code AS product_reference,
            pt.name->>'es_EC' AS product_name, 
            CASE 
                WHEN (pt.lead_time_fabrica + pt.lead_time_transporte) IS NULL THEN 0 
            ELSE (pt.lead_time_fabrica + pt.lead_time_transporte) 
            END AS lead_time_total, 
            pol.product_qty, pol.qty_received, 
            (pol.product_qty - pol.qty_received) AS cant_x_ingresar, pol.price_unit,
            (pol.product_qty - pol.qty_received) * pol.price_unit AS costo_faltante,
            pol.date_planned, pol.analytic_account_names,
            CASE
                WHEN po.purchase_order_type='product' THEN 'Producto'
                WHEN po.purchase_order_type='service' THEN 'Servicio'
                WHEN po.purchase_order_type='mixed' THEN 'Producto y Servicio'
            END AS tipo_orden,
            rpu.name AS creado_por, rpa.name AS aprobado_por, po.effective_date
        FROM purchase_order AS po
        INNER JOIN purchase_order_line AS pol ON po.id = pol.order_id
        INNER JOIN product_product AS pp ON pp.id = pol.product_id
        INNER JOIN product_template AS pt ON pt.id = pp.product_tmpl_id
        LEFT JOIN res_company AS rc ON po.company_id = rc.id
        LEFT JOIN res_partner AS rp ON po.partner_id = rp.id
        LEFT JOIN res_users AS ruc ON po.create_uid = ruc.id
        LEFT JOIN res_partner AS rpu ON ruc.partner_id = rpu.id
        LEFT JOIN res_users AS rua ON po.usuario_aprobacion_id = rua.id
        LEFT JOIN res_partner AS rpa ON rua.partner_id = rpa.id
        WHERE ((pol.product_qty - pol.qty_received) > 0) AND po.company_id IN %s  
        AND po.purchase_order_type = %s
        ORDER BY po.name, pp.default_code;
        """

        self.env.cr.execute(query, (company_ids, purchase_order_type,))
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
        return output.read(), 'xlsx', 'Reporte_OC_Tránsito.xlsx'

    def action_export_xlsx(self):
        data, file_format, file_name = self.generate_xlsx_report()

        # Crear un adjunto con el archivo generado
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': base64.b64encode(data),  # Codificar en base64
            'store_fname': file_name,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'purchase.transit.inventory.report',
            'res_id': self.id,
        })

        # Devolver la acción para descargar el archivo
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % attachment.id,
            'target': 'self',
        }

