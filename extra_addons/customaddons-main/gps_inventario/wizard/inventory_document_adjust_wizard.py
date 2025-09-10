# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from xlrd import open_workbook
from odoo.exceptions import ValidationError
from ...calendar_days.tools import CalendarManager,DateManager
from ...message_dialog.tools import FileManager
dtObj=DateManager()
clObj=CalendarManager()
flObj=FileManager()

class InventoryDocumentAdjustWizard(models.TransientModel):
    _name="inventory.document.adjust.wizard"
    _description="Asistente de Ajuste de Inventario"
    
    @api.model
    def get_default_movement_id(self):
        return self._context.get("active_ids",False) and self._context["active_ids"][0] or False
    
    @api.model
    def get_default_company_id(self):
        if self._context.get("active_ids",False):
            for brw_each in self.env["inventory.document.adjust"].sudo().browse(self._context["active_ids"]):
                return brw_each.company_id.id
        return False

    @api.model
    def get_default_date_from(self):
        if self._context.get("active_ids",False):
            for brw_each in self.env["inventory.document.adjust"].sudo().browse(self._context["active_ids"]):
                return brw_each.date_from or fields.Date.today()
        return False

    movement_id=fields.Many2one("inventory.document.adjust", "Ajuste de Inventario",required=False,default=get_default_movement_id)
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
        OBJ_PRODUCT= self.env["product.product"].sudo()
        OBJ_LOCATION=self.env["stock.location"].sudo()
        OBJ_LINE=self.env["inventory.document.adjust.line"].sudo()
        ACTIVE_LINE_ID,UBICACION_NAME, REFENCIA_ANTERIOR,DEFAULT_CODE,NAME, QUANTITY, COMMENTS = 0, 1, 2, 3,4,5,6
        for brw_each in self:
            line_ids = [ ]
            ext=flObj.get_ext(brw_each.file_name)
            fileName=flObj.create(ext)
            flObj.write(fileName, flObj.decode64(brw_each.file))
            book = open_workbook(fileName)
            sheet = book.sheet_by_index(0)
            active_lines=brw_each.movement_id.line_ids.filtered(lambda  x: x.origin=='original')
            delete_lines=brw_each.movement_id.line_ids.filtered(lambda  x: x.origin!='original')
            if delete_lines:
                delete_lines.unlink()
            active_line_ids=active_lines and active_lines.ids or []

            locations = brw_each.movement_id.get_all_locations()
            filter_location_ids = locations and locations.ids or []
            filter_location_ids+=[-1,-1]
            DEFAULT_CODE_COUNTERS={}
            LINE_COUNTERS = {}
            for row_index in range(5, sheet.nrows):
                excel_row=row_index+1
                line_value=sheet.cell(row_index, ACTIVE_LINE_ID).value
                line_id=0
                if line_value:
                    if type(line_value) in (int,float):
                        line_id = int(line_value)
                    else:
                        if line_value!="":
                            raise ValidationError(_("El # ID debe ser numerico o vacio revisa la fila %s") % (excel_row,))
                if line_id!=0:
                    if line_id not in active_line_ids:
                        raise ValidationError(_("EL # ID %s no esta presente en los registros originales descargados de la plantilla revisa la fila %s") % (line_id,excel_row))

                    if not LINE_COUNTERS.get(line_id, False):
                        LINE_COUNTERS[line_id] = 0
                    line_counter = LINE_COUNTERS[line_id] + 1
                    if line_counter > 1:
                        raise ValidationError(
                            _("Solo puedes definir una vez el # id a la vez revisa el codigo %s ,fila %s") % (
                            line_id, excel_row))
                    LINE_COUNTERS[line_id] = line_counter

                default_code = str(sheet.cell(row_index, DEFAULT_CODE).value)
                ubication_name = str(sheet.cell(row_index, UBICACION_NAME).value)

                pk="%s-%s" % (default_code,ubication_name)
                if not DEFAULT_CODE_COUNTERS.get(pk,False):
                    DEFAULT_CODE_COUNTERS[pk]=0
                counter= DEFAULT_CODE_COUNTERS[pk]+1
                if counter>1:
                    raise ValidationError(_("Solo puedes definir una vez un producto a la vez revisa el codigo %s ,fila %s") % (default_code,excel_row))
                DEFAULT_CODE_COUNTERS[pk]=counter

                qty_value=sheet.cell(row_index, QUANTITY).value
                if type(qty_value) not in (int, float):
                    raise ValidationError(_("La cantidad debe ser numerica revisa la fila %s") % (excel_row,))
                quantity = int(qty_value)
                comments = str(sheet.cell(row_index, COMMENTS).value)
                command_line=(line_id>0) and 1 or 0
                values = {
                    "quantity": quantity,
                    "comments": comments,
                }
                if command_line==1:
                    brw_line=OBJ_LINE.browse(line_id)
                    if default_code!=brw_line.product_id.default_code:
                        raise ValidationError(_("El codigo del archivo %s ,no es el mismo al del registro %s , %s revisa la fila %s") % (default_code,brw_line.id,brw_line.product_id.default_code,excel_row))
                    line_ids.append((command_line,line_id, values))
                else:
                    srch_product=OBJ_PRODUCT.search([('default_code','=',default_code)])
                    if not srch_product:
                        raise ValidationError(_("No hay producto con codigo %s ,revisa la fila %s") % (default_code,excel_row))
                    if len(srch_product)>1:
                        raise ValidationError(
                            _("Existe mas de un producto con codigo %s en la base de datos ,revisa la fila %s") % (default_code, excel_row))

                    ####
                    srch_location = OBJ_LOCATION.search([('id','in',filter_location_ids),('name', '=', ubication_name)])
                    if not srch_location:
                        raise ValidationError(
                            _("No hay ubicacion con nombre %s ,revisa la fila %s") % (ubication_name, excel_row))
                    if len(srch_location) > 1:
                        raise ValidationError(
                            _("Existe mas de una ubicacion con nombre %s en la base de datos ,revisa la fila %s") % (
                            ubication_name, excel_row))

                    values.update({
                        "origin":"manual",
                        "stock_location_id":srch_location[0].id ,
                        "product_id":srch_product[0].id ,
                        "name":srch_product[0].name,
                        "apply":True
                    })
                    line_ids.append((command_line, 0, values))
            brw_each.movement_id.write({"line_ids":line_ids})
            brw_each.movement_id.action_update_stock()
        return True
