# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _,SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
import base64
import xlsxwriter
import io

class MaterialPurchaseOrder(models.Model):
    _inherit = 'material.purchase.requisition'

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
            headers = ['#ID','Producto','Descripcion', 'Rubro', 'CtaAnalitica','Unidad', 'Cantidad', 'Precio Unitario', 'Precio Venta','Precio Total']
            for col, header in enumerate(headers):
                sheet.write(row, col, header, header_format)
            row = row + 1
            sum = 0
            for line in record.requisition_line_ids:
                sheet.write(row, 0, line.id)
                sheet.write(row, 1, line.product_id.default_code or '')
                sheet.write(row, 2, line.description if line.description else line.name or '')
                sheet.write(row, 3, line.rubro or '')
                sheet.write(row, 4, line.analytic_account_id.name or '')
                sheet.write(row, 5, line.product_id.uom_po_id.name or '')
                sheet.write(row, 6, line.qty)
                sheet.write(row, 7, line.price_unit)
                if self.env.user.has_group('account_payment_purchase.group_analytic_user'):
                    sheet.write(row, 8, line.precio_venta)
                else:
                    sheet.write(row, 8, 0)
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
        'material.purchase.requisition.detail',
        'order_id',
        string='Detalles',
    )

    def requisition_confirm(self):
        for requisition in self:
            if not requisition.requisition_line_ids.to_validate():
                raise ValidationError(_("Error en Validacion."))
        return super(MaterialPurchaseOrder, self).requisition_confirm()

    def manager_approve(self):
        for requisition in self:
            if not requisition.requisition_line_ids.to_validate():
                raise ValidationError(_("Error en Validacion.."))
        return super(MaterialPurchaseOrder, self).manager_approve()

    def user_approve(self):
        for requisition in self:
            if not requisition.requisition_line_ids.to_validate():
                raise ValidationError(_("Error en Validacion..."))
        return super(MaterialPurchaseOrder, self).user_approve()

class MaterialPurchaseOrderDetail(models.Model):
    _name = 'material.purchase.requisition.detail'
    _description = 'Detalle de Requisición de Compra de Material'

    order_id = fields.Many2one(
        'material.purchase.requisition',
        string='Orden de Requisición',
        ondelete='cascade',  # Elimina los detalles cuando se elimina la orden
    )
    descripcion = fields.Char(
        string='Descripción',
    )


class MaterialPurchaseRequisition(models.Model):
    _inherit = "material.purchase.requisition"

    @api.model
    def _prepare_po_line(self, line=False, purchase_order=False):
        """Prepare the values to create a purchase order line from a requisition line."""
        vals = super(MaterialPurchaseRequisition, self)._prepare_po_line(line, purchase_order)
        if not self.requisition_line_ids.to_validate():
            raise ValidationError(_("Error en Validacion..."))
        if line.asigna_custodio:
            vals.update({
                # 'asigna_custodio': line.asigna_custodio,
                'employees_ids': [(6, 0, line.employees_ids.ids)],
            })
        return vals


class MaterialPurchaseRequisitionLine(models.Model):
    _inherit = 'material.purchase.requisition.line'

    asigna_custodio = fields.Boolean(string="Asignar Custodio?", default=False)
    employees_ids = fields.Many2many(
        comodel_name="hr.employee",
        string="Employees",
    )

    @api.onchange('asigna_custodio')
    def _onchange_asigna_custodio(self):
        if self.asigna_custodio:
            return {
                'domain': {'employees_ids': [('active', '=', True)]},
                'warning': {
                    'title': _("Aviso"),
                    'message': _("Seleccione los empleados a los que se asignará el producto."),

                },
            }
        else:
            self.employees_ids = False
            
    @api.model_create_multi
    def create(self, vals):
        res = super(MaterialPurchaseRequisitionLine, self).create(vals)
        for line in res:
            if not line.to_validate():
                raise UserError(_(" '%s' ", line.name))
        return res

    def write(self, vals):
        res = super(MaterialPurchaseRequisitionLine, self).write(vals)
        for line in self:
            if not line.to_validate():
                raise UserError(_("No se puede modificar la línea de requisición '%s' porque no está en estado borrador o cancelado.", line.name))
        return res

    def to_validate(self):
        for line in self:
            if line.qty <= 0:
                raise UserError(_("Coloque la cantidad al producto '%s'.", line.product_id.default_code))
            if line.asigna_custodio and line.requisition_type == 'purchase':
                if not (len(line.employees_ids.ids) == int(line.qty)):
                    raise UserError(_("El producto '%s' debe ser asignado a la misma cantidad de empleados.",line.product_id.default_code))
            else:
                if (len(line.employees_ids.ids) > 0):
                    raise UserError(_("El producto '%s', no debe de ser asignado a empleados.", line.product_id.default_code))
        return True