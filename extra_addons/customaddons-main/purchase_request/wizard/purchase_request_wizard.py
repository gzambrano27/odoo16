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
from openpyxl import load_workbook

class PurchaseRequestWizard(models.TransientModel):
    _name="purchase.request.wizard"
    _description="Asistente de Requisicion de Compra"
    
    @api.model
    def get_default_movement_id(self):
        return self._context.get("active_ids",False) and self._context["active_ids"][0] or False
    
    @api.model
    def get_default_company_id(self):
        if self._context.get("active_ids",False):
            for brw_each in self.env["purchase.request"].sudo().browse(self._context["active_ids"]):
                return brw_each.company_id.id
        return False


    movement_id=fields.Many2one("purchase.request", "Requisicion",required=False,default=get_default_movement_id)
    company_id=fields.Many2one("res.company",string="Compañia",required=False,default=get_default_company_id)
    currency_id = fields.Many2one("res.currency", "Moneda", related="company_id.currency_id", store=False,
                                  readonly=True)
    origin=fields.Selection([('file','Archivo'),],string="Origen",default='file')
    file=fields.Binary("Archivo",required=False,filters='*.xlsx')
    file_name=fields.Char("Nombre de Archivo",required=False,size=255)
    
    

    def process(self):
        for brw_each in self:
            if brw_each.origin=="file":
                brw_each.process_file()
        return True
    
    def process_file(self):
        OBJ_PRODUCT = self.env["product.product"].sudo()
        OBJ_ANALITICA = self.env["account.analytic.account"].sudo()
        OBJ_LOCATION = self.env["stock.location"].sudo()
        OBJ_LINE = self.env["purchase.request.line"].sudo()
        ACTIVE_LINE_ID, Producto, Descripcion, CtaAnalitica, Unidad, Cantidad,Empleados,UnSoloCustodio = 0, 1, 2, 3, 4, 5,6,7
        for brw_each in self:
            line_ids = []
            ext = flObj.get_ext(brw_each.file_name)
            fileName = flObj.create(ext)
            flObj.write(fileName, flObj.decode64(brw_each.file))
    
            # Cargar el archivo con openpyxl
            book = load_workbook(fileName, data_only=True)
            sheet = book.active  # Selecciona la hoja activa
        
            for row_index, row in enumerate(sheet.iter_rows(min_row=4, values_only=True), start=4):  # Comienza desde la fila 4
                line_value = row[ACTIVE_LINE_ID]
                line_id = int(line_value) if isinstance(line_value, (int, float)) else 0

                # Este código se mantiene igual que el original, adaptando cómo se acceden a los valores de las celdas.
                default_code = str(row[Producto] or '').strip()
                employee_raw = row[Empleados] or ''
                employee_codes = [
                    ('0' + code.strip()) if len(code.strip()) == 9 else code.strip()
                    for code in str(employee_raw).split(',')
                    if code.strip()
                ]
                employee_codes = list(set(employee_codes))  # 🔁 Elimina duplicados

                employee_ids = self.env['hr.employee'].sudo().search([('identification_id', 'in', employee_codes)])
                if len(employee_codes) != len(employee_ids):
                    raise UserError(f"Algunos empleados no encontrados en: {employee_codes}")
                un_solo_custodio = row[UnSoloCustodio]
                qty_value = row[Cantidad]
                descripcion = row[Descripcion]
                ctaanalitica = row[CtaAnalitica]
                quantity = qty_value
                if not isinstance(qty_value, (int, float)):
                    raise ValidationError(_("La cantidad debe ser numérica. Revisa la fila %s") % (row_index,))
                if not default_code:
                    continue
                srch_product = OBJ_PRODUCT.search([('default_code', '=', default_code)])
                if not srch_product:
                    raise ValidationError(_("No hay producto con código %s. Revisa la fila %s") % (default_code, row_index))
                if len(srch_product) > 1:
                    raise ValidationError(_("Existe más de un producto con código %s en la base de datos. Revisa la fila %s") % (default_code, row_index))    
                srch_cta = ''
                if ctaanalitica:
                    srch_cta = OBJ_ANALITICA.search([('name', '=', ctaanalitica),('company_id', '=', self.company_id.id)])
                    if not srch_cta:
                        raise ValidationError(_("No hay cuenta analitica con nombre %s. Revisa la fila %s") % (ctaanalitica, row_index))

                values = {
                    "product_qty": quantity,
                    "product_id": srch_product[0].id,
                    "name": descripcion,
                    'product_uom_id': srch_product[0].uom_po_id.id,
                    'analytic_distribution': {str(srch_cta[0].id): 100},
                    'employees_ids': [(6, 0, employee_ids.ids)],
                    'un_solo_custodio': un_solo_custodio,
                }
                line_ids.append((1 if line_id > 0 else 0, line_id, values))
            brw_each.movement_id.write({"line_ids": line_ids})
        return True