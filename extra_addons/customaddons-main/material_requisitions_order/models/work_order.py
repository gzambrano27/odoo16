# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _,SUPERUSER_ID
from odoo.exceptions import ValidationError
import base64
import xlsxwriter
import io

class MaterialPurchaseOrder(models.Model):
    _inherit = 'material.requisition.order'

    file_data = fields.Binary(string="Archivo Excel", readonly=True)
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Cuenta Analítica',
        domain=lambda self: self._get_analytic_domain(),
    )

    def _get_analytic_domain(self):
    # Verificar si el registro tiene una compañía asignada
        if self.company_id:
            return [('company_id', '=', self.company_id.id)]
        else:
            # Si no hay compañía en el registro, usar la compañía activa del usuario
            return [('company_id', '=', self.env.company.id)]
    

    def button_descargar(self):
        for record in self:
            # Crear el archivo Excel en memoria
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output)
            sheet = workbook.add_worksheet('MaterialRequisition')

            # Formatos
            title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
            header_format = workbook.add_format({'bold': True, 'align': 'left'})
            value_format = workbook.add_format({'align': 'left'})

            # Cabecera principal
            #sheet.merge_range('A1:D1', record.company_id.name, title_format)
            sheet.write('A1', record.company_id.name, title_format)
            #sheet.merge_range('E1:H1', 'AJUSTE DE INVENTARIO', title_format)
            sheet.write('G1', 'MATERIAL DE REQUISICION', title_format)

            # Detalles de la cabecera
            sheet.write('A2', 'EMPLEADO:', header_format)

            sheet.write('A3', 'PROVEEDOR:', header_format)

            
            # Espaciado para la tabla
            row = 2
            # Encabezados de la tabla
            headers = ['#ID','Producto','Descripcion', 'Unidad', 'Cantidad']
            for col, header in enumerate(headers):
                sheet.write(row, col, header, header_format)
            row = row + 1
            sum = 0
            for line in record.requisition_line_ids:
                sheet.write(row, 0, line.id)
                sheet.write(row, 1, line.product_id.default_code or '')
                sheet.write(row, 2, line.description or '')
                sheet.write(row, 3, line.product_id.uom_po_id.name or '')
                sheet.write(row, 4, line.qty)
                #sheet.write(row, 9, line.qty * line.price_unit)
                #sum = sum + (line.qty * line.price_unit)
                row += 1
            #sheet.write(row, 9, sum)
            # Guardar el archivo en memoria
            workbook.close()
            output.seek(0)

            # Convertir el archivo a base64 y guardarlo en el campo
            record.file_data = base64.b64encode(output.read())
            output.close()

        # Retornar acción para descargar el archivo
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/file_data/{self.name}.xlsx',
            'target': 'self',
        }

    cliente_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        domain=[('is_company', '=', True)],  # Solo compañías
    )
    department_carried_out = fields.Many2one(
        'hr.department',
        string='Departamento a Realizar',
    )
    proyecto = fields.Char(
        string='Proyecto',
    )
    estacion = fields.Char(
        string='Estación',
    )
    motivo = fields.Char(
        string='Motivo',
    )
    observaciones_producto = fields.Text(
        string='Observacion de los productos',
    )
    observaciones = fields.Text(
        string='Observaciones de la orden de compra',
    )

    # Campos relacionados con empleados
    ingenieria_id = fields.Many2one(
        'hr.employee',
        string='Ingeniería',
    )
    diseno_id = fields.Many2one(
        'hr.employee',
        string='Diseño',
    )
    revisado_id = fields.Many2one(
        'hr.employee',
        string='Revisado',
    )
    fabrica_id = fields.Many2one(
        'hr.employee',
        string='Fábrica',
    )

    # Relación One2many con el modelo de detalles
    detalles_ids = fields.One2many(
        'material.requisition.order.detail',
        'order_id',
        string='Detalles',
    )

class MaterialPurchaseOrderDetail(models.Model):
    _name = 'material.requisition.order.detail'
    _description = 'Detalle de Requisición de Compra de Material'

    order_id = fields.Many2one(
        'material.requisition.order',
        string='Orden de Requisición',
        ondelete='cascade',  # Elimina los detalles cuando se elimina la orden
    )
    descripcion = fields.Char(
        string='Descripción',
    )