from odoo import models
from datetime import datetime

class ImportationReportXlsx(models.AbstractModel):
    _name = 'report.ecua_foreign_purchase.importation_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Reporte de Importación XLSX'

    def generate_xlsx_report(self, workbook, data, objects):
        # Formatos
        bold = workbook.add_format({'bold': True, 'border': 1, 'align': 'center'})
        normal = workbook.add_format({'border': 1})
        money = workbook.add_format({'num_format': '#,##0.00', 'border': 1})

        for o in objects:
            sheet = workbook.add_worksheet(o.name or 'Importación')

            # Encabezado
            sheet.merge_range('A1:G1', f'Reporte de Importación - {o.name}', bold)

            sheet.write(2, 0, "Proveedor(es)", bold)
            sheet.write(2, 1, o.provider_names or '')
            sheet.write(3, 0, "País Origen", bold)
            sheet.write(3, 1, o.country_id.name or '')
            sheet.write(4, 0, "Contenedor", bold)
            sheet.write(4, 1, o.container_info or '')
            sheet.write(5, 0, "Fecha", bold)
            sheet.write(5, 1, str(o.creation_date or ''))

            # Totales
            row = 7
            sheet.write(row, 0, "FOB Total", bold)
            sheet.write(row, 1, o.total_only_foreign, money)
            row += 1
            sheet.write(row, 0, "Flete", bold)
            sheet.write(row, 1, o.freight_total, money)
            row += 1
            sheet.write(row, 0, "Seguro", bold)
            sheet.write(row, 1, o.insurance_total, money)
            row += 1
            sheet.write(row, 0, "Factor Aproximación", bold)
            factor = (o.freight_total + o.insurance_total) / (o.total_only_foreign or 1)
            sheet.write(row, 1, factor, money)
            row += 1
            sheet.write(row, 0, "ISD", bold)
            sheet.write(row, 1, o.total_isd, money)
            row += 1
            sheet.write(row, 0, "Aranceles", bold)
            sheet.write(row, 1, o.total_arancel_amount_distribution, money)
            row += 1
            sheet.write(row, 0, "IVA Importación", bold)
            sheet.write(row, 1, o.liq_iva_import, money)
            row += 1
            sheet.write(row, 0, "Costo Total", bold)
            sheet.write(row, 1, o.liq_total_cost, money)

            # Detalle de Productos
            row += 2
            sheet.write(row, 0, "Producto", bold)
            sheet.write(row, 1, "Partida", bold)
            sheet.write(row, 2, "Cantidad", bold)
            sheet.write(row, 3, "Unidad de Medida", bold)
            sheet.write(row, 4, "FOB Unitario", bold)
            sheet.write(row, 5, "FOB Total", bold)
            sheet.write(row, 6, "Participación", bold)
            sheet.write(row, 7, "Gastos FOB", bold)
            sheet.write(row, 8, "Flete Internacional", bold)
            sheet.write(row, 9, "Seguro en Aduana", bold)
            sheet.write(row, 10, "Gasto Totales", bold)
            sheet.write(row, 11, "% Arancel", bold)
            sheet.write(row, 12, "Advaloren", bold)
            sheet.write(row, 13, "Fodinfa", bold)
            sheet.write(row, 14, "Arancel Total", bold)
            sheet.write(row, 15, "CIF Total", bold)
            sheet.write(row, 16, "Costo Antes ISD", bold)
            sheet.write(row, 17, "Total ISD", bold)
            sheet.write(row, 18, "Costo Después ISD", bold)
            sheet.write(row, 19, "Número de Factura", bold)
            sheet.write(row, 20, "Factor", bold)
            sheet.write(row, 21, "Costo Unitario", bold)
            row += 1

            for line in o.importation_rnote_ids:
                total_gastos_importacion = sum(line.importation_id.liquidation_line_ids.mapped('amount'))
                tot = line.importation_id.liq_fob + total_gastos_importacion
                costo_prorrateado = line.price_subtotal * factor
                factor_aprox = tot/line.importation_id.liq_fob
                sheet.write(row, 0, line.product_id.display_name or '', normal)
                sheet.write(row, 1, line.partida_arancelaria or '', normal)
                sheet.write(row, 2, line.product_qty, normal)
                sheet.write(row, 3, line.product_id.uom_id.name, normal)
                sheet.write(row, 4, line.price_subtotal/line.product_qty, money)
                sheet.write(row, 5, line.price_subtotal, money)
                sheet.write(row, 6, (line.price_subtotal/line.importation_id.liq_fob)*100, normal)
                sheet.write(row, 7, 0, normal)
                sheet.write(row, 8, 0, normal)
                sheet.write(row, 9, 0, normal)
                sheet.write(row, 10, 0, normal)
                sheet.write(row, 11, 0, normal)
                sheet.write(row, 12, 0, normal)
                sheet.write(row, 13,line.price_subtotal*0.5/100, normal)
                sheet.write(row, 14,line.price_subtotal*0.5/100, normal)
                sheet.write(row, 15,line.price_subtotal, normal)
                sheet.write(row, 16, line.price_unit_import, money)
                sheet.write(row, 17, line.price_total_import, money)
                sheet.write(row, 18, line.price_total_import, money)
                sheet.write(row, 19, line.price_total_import, money)
                sheet.write(row, 20, factor_aprox, normal)
                sheet.write(row, 21, line.price_total_import, money)
                row += 1
