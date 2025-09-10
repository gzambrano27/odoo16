# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from xlrd import open_workbook
import base64
import tempfile
import xlrd
from odoo.exceptions import ValidationError,UserError
from ...calendar_days.tools import CalendarManager,DateManager
from ...message_dialog.tools import FileManager
dtObj=DateManager()
clObj=CalendarManager()
flObj=FileManager()

class InventoryDocumentTransferWizard(models.TransientModel):
    _name="inventory.document.transfer.wizard"
    _description="Asistente de Transferencia de Inventario"
    
    @api.model
    def get_default_movement_id(self):
        return self._context.get("active_ids",False) and self._context["active_ids"][0] or False
    
    @api.model
    def get_default_company_id(self):
        if self._context.get("active_ids",False):
            for brw_each in self.env["inventory.document.transference"].sudo().browse(self._context["active_ids"]):
                return brw_each.company_id.id
        return False

    @api.model
    def get_default_date_from(self):
        if self._context.get("active_ids",False):
            for brw_each in self.env["inventory.document.transference"].sudo().browse(self._context["active_ids"]):
                return brw_each.date_from or fields.Date.today()
        return False

    movement_id=fields.Many2one("inventory.document.transference", "Transferencia de Inventario",required=False,default=get_default_movement_id)
    company_id=fields.Many2one("res.company",string="Compañia",required=False,default=get_default_company_id)
    currency_id = fields.Many2one("res.currency", "Moneda", related="company_id.currency_id", store=False,
                                  readonly=True)
    origin=fields.Selection([('file','Archivo'),],string="Origen",default='file')
    file=fields.Binary("Archivo",required=False,filters='*.xlsx')
    file_name=fields.Char("Nombre de Archivo",required=False,size=255)
    date_from=fields.Date("Fecha de Ajuste",required=False,default=get_default_date_from)

    def process(self):
        for brw_each in self:
            if brw_each.origin=="file":
                brw_each.process_file()
        return True

    def process_file(self):
        OBJ_PRODUCT = self.env["product.product"].sudo()
        OBJ_LINE = self.env["inventory.document.transference.line"].sudo()
        CANTIDAD, REFERENCIA = 0, 1
        for brw_each in self:
            line_ids = []

            # Verifica que el archivo tenga la extensión correcta
            if not brw_each.file_name or (not brw_each.file_name.endswith('.xls') and not brw_each.file_name.endswith('.xlsx')):
                raise UserError(_('El archivo debe ser un archivo Excel con extensión .xls o .xlsx.'))

            # Decodifica y guarda temporalmente el archivo
            try:
                file_data = base64.b64decode(brw_each.file)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xls" if brw_each.file_name.endswith('.xls') else ".xlsx") as tmp:
                    tmp.write(file_data)
                    tmp_path = tmp.name
            except Exception as e:
                raise UserError(_('Error al leer el archivo: %s') % e)

            # Lee el archivo Excel
            try:
                workbook = xlrd.open_workbook(tmp_path)
                sheet = workbook.sheet_by_index(0)  # Toma la primera hoja
            except Exception as e:
                raise UserError(_('Error al procesar el archivo Excel: %s') % e)

            active_lines = brw_each.movement_id.line_ids.filtered(lambda x: x.origin == 'original')
            delete_lines = brw_each.movement_id.line_ids.filtered(lambda x: x.origin != 'original')
            if delete_lines:
                delete_lines.unlink()

            active_line_ids = active_lines and active_lines.ids or []


            line_ids = []

            for row_index in range(5, sheet.nrows):  # Comienza desde la fila 6
                excel_row = row_index + 1

                qty_value = sheet.cell(row_index, CANTIDAD).value
                if not isinstance(qty_value, (int, float)):
                    raise ValidationError(_("La cantidad debe ser numérica. Revisa la fila %s") % excel_row)
                quantity = int(qty_value)

                referencia = str(sheet.cell(row_index, REFERENCIA).value)
                srch_product = OBJ_PRODUCT.search([('default_code', '=', referencia)])
                if not srch_product:
                    raise ValidationError(_("No hay producto con código %s. Revisa la fila %s") % (referencia, excel_row))
                if len(srch_product) > 1:
                    raise ValidationError(
                        _("¿Más de un producto con el código %s? Revisa la fila %s") % (referencia, excel_row))

                values = {
                    "quantity": quantity,
                    "product_id": srch_product[0].id,
                    "name": "prueba",
                }
                line_ids.append((0, 0, values))  # Agrega la estructura correcta

            brw_each.movement_id.write({"line_ids": line_ids})

        return True
