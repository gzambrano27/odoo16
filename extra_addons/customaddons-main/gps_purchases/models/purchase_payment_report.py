# -*- coding: utf-8 -*-
from odoo import models, fields, api
import io
import xlsxwriter
import base64

class PurchasePaymentReport(models.TransientModel):
    _name = 'purchase.payment.report'
    _description = 'Reporte de Pagos de Órdenes de Compra'

    company_ids = fields.Many2many(
        'res.company',
        string="Compañías",
        default=lambda self: self.env.company,
        domain=lambda self: [('id', 'in', self.env.user.company_ids.ids)]
    )

    purchase_order_type = fields.Selection(
        [('service', 'Servicio'), ('product', 'Producto'), ('mixed', 'Producto y Servicio')],
        string="Tipo de Orden de Compra",
        default=False
    )

    report_file = fields.Binary("Archivo del Reporte", readonly=True)
    report_file_name = fields.Char("Nombre del Archivo")

    def generate_xlsx_report(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Pagos Órdenes')

        # Formato de encabezado
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})
        data_format = workbook.add_format({'border': 1})

        # Encabezados
        headers = [
            'Empresa', 'Orden de Compra', 'Tipo de OC', 'Proveedor', 'Total OC',
            'Total Facturado', 'Monto Restante', 'Estado de Pago'
        ]

        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)

        company_ids = tuple(self.company_ids.ids) if self.company_ids else (self.env.company.id,)
        purchase_order_type = self.purchase_order_type

        query = """
        SELECT 
            rc.name AS company_name, po.name AS order_name,
            CASE
                WHEN po.purchase_order_type='product' THEN 'Producto'
                WHEN po.purchase_order_type='service' THEN 'Servicio'
                WHEN po.purchase_order_type='mixed' THEN 'Producto y Servicio'
            END AS tipo_orden,
            rp.name AS supplier_name, po.amount_total AS total_amount_OC,
            COALESCE(SUM(am.amount_total), 0) AS total_amount_FAC, 
            po.amount_total - COALESCE(SUM(am.amount_total), 0) AS remaining_amount,
            CASE
                WHEN COALESCE(SUM(am.amount_total), 0) = 0 THEN 'Sin pagos'
                WHEN COALESCE(SUM(am.amount_total), 0) < po.amount_total THEN 'Con anticipo'
                WHEN COALESCE(SUM(am.amount_total), 0) = po.amount_total THEN 'Pagada completamente'
                WHEN COALESCE(SUM(am.amount_total), 0) > po.amount_total THEN 'Sobrepago'
            END AS payment_status
        FROM purchase_order po
        LEFT JOIN account_move am ON am.invoice_origin = po.name 
            AND am.move_type = 'in_invoice' 
            AND am.state = 'posted'
        LEFT JOIN res_partner rp ON po.partner_id = rp.id
        LEFT JOIN res_company rc ON po.company_id = rc.id
        WHERE po.company_id IN %s
        """

        # Agregar condición de `purchase_order_type` solo si se seleccionó un tipo
        query_params = [company_ids]

        if purchase_order_type:
            query += " AND po.purchase_order_type = %s"
            query_params.append(purchase_order_type)
        else:
            query += " AND po.purchase_order_type IN ('product', 'service', 'mixed')"

        query += """
        GROUP BY po.id, po.name, po.partner_id, rp.name, po.amount_total, rc.name, po.company_id
        HAVING COALESCE(SUM(am.amount_total), 0) > 0
        ORDER BY rp.name;
        """

        # Ejecutar la consulta con parámetros
        self.env.cr.execute(query, tuple(query_params))
        records = self.env.cr.fetchall()

        # Insertar datos en el Excel
        for row_num, record in enumerate(records, start=1):
            for col_num, value in enumerate(record):
                sheet.write(row_num, col_num, value, data_format)

        workbook.close()
        output.seek(0)
        file_data = output.getvalue()
        output.close()

        return file_data

    def action_export_xlsx(self):
        file_data = self.generate_xlsx_report()
        file_name = "reporte_pagos_oc.xlsx"

        # Convertir el archivo en base64
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': base64.b64encode(file_data),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        # Adjuntar el archivo al registro
        self.write({
            'report_file': attachment.datas,
            'report_file_name': file_name
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment.id}?download=true",
            'target': 'self',
        }
