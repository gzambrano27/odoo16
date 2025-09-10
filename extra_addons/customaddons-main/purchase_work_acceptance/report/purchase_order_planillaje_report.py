from odoo import models
from odoo.tools import date_utils
import io
import xlsxwriter
from odoo.http import content_disposition
from datetime import datetime
import base64
import os
from odoo.modules.module import get_module_resource


class PurchaseOrderPlanillajeReport(models.AbstractModel):
    _name = 'report.purchase_work_acceptance.planillaje_report'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Resumen de Planillaje por Orden de Compra'

    def create_xlsx_report(self, docids, data):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        orders = self.env['purchase.order'].browse(docids)
        self.generate_xlsx_report(workbook, data, orders)
        workbook.close()
        output.seek(0)
        return output.read(), 'xlsx'
    

    def _get_report_values(self, docids, data=None):
        orders = self.env['purchase.order'].browse(docids)
        return {
            'docs': orders,
        }
    
    def generate_xlsx_report(self, workbook, data, orders):
        logo_path = get_module_resource('purchase_work_acceptance', 'static/description', 'logo_gps.png')

        for order in orders:
            sheet = workbook.add_worksheet(order.name[:31])
            sheet.set_zoom(90)
            sheet.set_column('A:Z', 12)

            # FORMATS
            title_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 16})
            subtitle_format = workbook.add_format({'align': 'left', 'font_size': 12})
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center'})
            subheader_format = workbook.add_format({'bold': True, 'bg_color': '#BDD7EE', 'border': 1, 'align': 'center'})
            normal_format = workbook.add_format({'border': 1, 'align': 'center'})
            money_format = workbook.add_format({'num_format': '$#,##0.00', 'border': 1, 'align': 'right'})
            percent_format = workbook.add_format({'num_format': '0.00%', 'border': 1, 'align': 'right'})
            bold_money = workbook.add_format({'num_format': '$#,##0.00', 'border': 1, 'align': 'right', 'bold': True})
            bold_normal = workbook.add_format({'border': 1, 'align': 'center', 'bold': True})
            bold_percent = workbook.add_format({'num_format': '0.00%', 'border': 1, 'align': 'right', 'bold': True})
            bold_qty = workbook.add_format({'border': 1, 'align': 'center', 'bold': True})

            # PREPARAR PLANILLAS
            wa_lines = self.env['work.acceptance.line'].search([('wa_id.purchase_id', '=', order.id)])
            planillas = sorted(set(wa_line.wa_id for wa_line in wa_lines), key=lambda w: w.date_accept or w.date_receive or w.date_due)

            base_headers = ['ITEM', 'DESCRIPCIÓN', 'UNIDAD', 'CANT. CONTR.', 'P. UNIT. (US $)', 'SUBTOTAL (US $)']
            planilla_headers = [(f'PLANILLA {i}', ['CANT.', 'TOTAL ($)']) for i, _ in enumerate(planillas, 1)]
            resumen_headers = ['ACUMULADO A LA FECHA', 'SALDO']
            resumen_subs = ['CANT.', 'TOTAL ($)']
            extra_headers = ['% AVANCE']

            total_columns = len(base_headers) + len(planilla_headers) * 2 + len(resumen_headers) * 2 + len(extra_headers)
            last_col_letter = xlsxwriter.utility.xl_col_to_name(total_columns - 1)

            # TÍTULO Y LOGO
            sheet.merge_range(f'A1:{last_col_letter}1', 'RESUMEN DE PLANILLAS POR ORDEN DE SERVICIO', title_format)
            sheet.merge_range(f'A2:C2', f'ORDEN DE COMPRA: {order.name}', subtitle_format)
            sheet.insert_image(f'{last_col_letter}1', logo_path, {'x_scale': 0.3, 'y_scale': 0.3, 'x_offset': 5, 'y_offset': 2})

            # ENCABEZADOS AGRUPADOS: fila 3 para secciones, fila 4 para títulos
            col = 0
            sheet.merge_range(2, col, 2, col + len(base_headers) - 1, 'CONTRATO / ORDEN DE SERVICIO', subheader_format)
            for i, head in enumerate(base_headers):
                sheet.write(3, i, head, header_format)
            col += len(base_headers)
            for label, subs in planilla_headers:
                sheet.merge_range(2, col, 2, col + len(subs) - 1, label, subheader_format)
                for i, sub in enumerate(subs):
                    sheet.write(3, col + i, sub, header_format)
                col += len(subs)
            for label in resumen_headers:
                sheet.merge_range(2, col, 2, col + len(resumen_subs) - 1, label, subheader_format)
                for i, sub in enumerate(resumen_subs):
                    sheet.write(3, col + i, sub, header_format)
                col += len(resumen_subs)
            sheet.merge_range(2, col, 3, col, extra_headers[0], subheader_format)

            row = 4
            totals = [0.0] * total_columns

            for idx, line in enumerate(order.order_line, 1):
                subtotal = line.product_qty * line.price_unit
                sheet.write(row, 0, idx, normal_format)
                sheet.write(row, 1, line.name or '', normal_format)
                sheet.write(row, 2, line.product_uom.name or '', normal_format)
                sheet.write(row, 3, line.product_qty, normal_format)
                sheet.write(row, 4, line.price_unit, money_format)
                sheet.write(row, 5, subtotal, money_format)

                totals[3] += line.product_qty
                totals[5] += subtotal

                acumulado_cant = 0.0
                acumulado_total = 0.0
                col = 6

                for i, wa in enumerate(planillas):
                    wa_line = wa.wa_line_ids.filtered(lambda l: l.purchase_line_id.id == line.id)
                    qty = sum(wa_line.mapped('product_qty'))
                    total = qty * line.price_unit
                    acumulado_cant += qty
                    acumulado_total += total
                    sheet.write(row, col, qty, normal_format)
                    sheet.write(row, col + 1, total, money_format)
                    totals[col] += qty
                    totals[col + 1] += total
                    col += 2

                saldo_cant = line.product_qty - acumulado_cant
                saldo_total = saldo_cant * line.price_unit
                avance = acumulado_cant / line.product_qty if line.product_qty else 0.0

                sheet.write(row, col, acumulado_cant, normal_format)
                sheet.write(row, col + 1, acumulado_total, money_format)
                sheet.write(row, col + 2, saldo_cant, normal_format)
                sheet.write(row, col + 3, saldo_total, money_format)
                sheet.write(row, col + 4, avance, percent_format)

                totals[col] += acumulado_cant
                totals[col + 1] += acumulado_total
                totals[col + 2] += saldo_cant
                totals[col + 3] += saldo_total
                totals[col + 4] += avance

                row += 1

            # TOTALES
            sheet.write(row, 1, 'TOTALES', bold_normal)
            for i, val in enumerate(totals):
                if i in [0, 1, 2, 4, 5]:
                    sheet.write(row, i, '', bold_normal)  # dejar vacío
                elif i == len(totals) - 1:
                    sheet.write(row, i, val / len(order.order_line), bold_percent)
                elif i in [3] + list(range(6, len(totals)-5, 2)) + [len(totals)-5, len(totals)-3]:
                    sheet.write(row, i, val, bold_qty)
                else:
                    sheet.write(row, i, val, bold_money)