# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from xlrd import open_workbook
from odoo.exceptions import ValidationError
from ...calendar_days.tools import CalendarManager, DateManager
from ...message_dialog.tools import FileManager

dtObj = DateManager()
clObj = CalendarManager()
flObj = FileManager()


class StockPickingImportWizard(models.TransientModel):
    _name = "stock.picking.import.wizard"
    _description = "Asistente de Importar Picking"

    @api.model
    def get_default_movement_id(self):
        return self._context.get("active_ids", False) and self._context["active_ids"][0] or False


    movement_id = fields.Many2one("stock.picking", "Importar Picking", required=False,
                                  default=get_default_movement_id)
    company_id = fields.Many2one("res.company", string="Compañia", required=False)
    origin = fields.Selection([('file', 'Archivo'), ], string="Origen", default='file')
    file = fields.Binary("Archivo", required=False, filters='*.xlsx')
    file_name = fields.Char("Nombre de Archivo", required=False, size=255)

    def _get_virtual_location_id(self):
        self.ensure_one()
        brw_company=self.company_id
        srch = self.env["stock.location"].sudo().search([('company_id', '=', brw_company.id),
                                                             ('usage', '=', 'inventory')
                                                             ])
        return srch and srch[0].id or False

    @api.model
    def _get_picking_type(self, brw_company, brw_location_id, code):
        field_ky='default_location_dest_id'
        if code=='outgoing':
            field_ky = 'default_location_src_id'
        srch = self.env["stock.picking.type"].sudo().search([('company_id', '=', brw_company.id),
                                                             (field_ky, '=', brw_location_id.id),
                                                             ('code', '=', code)
                                                             ])
        if not srch:
            raise ValidationError(
                _("No existe tipo de operacion para %s para %s") % (code,brw_location_id.name), )
        return srch and srch[0].id or False

    def process(self):
        for brw_each in self:
            if brw_each.origin == "file":
                brw_each.process_file()
        return True

    def process_file(self):
        OBJ_PRODUCT = self.env["product.product"].sudo()
        DEFAULT_CODE, NAME, QUANTITY = 0, 1, 2,
        for brw_each in self:
            move_ids_without_package = [(5,)]
            ext = flObj.get_ext(brw_each.file_name)
            fileName = flObj.create(ext)
            flObj.write(fileName, flObj.decode64(brw_each.file))
            book = open_workbook(fileName)
            sheet = book.sheet_by_index(0)
            DEFAULT_CODE_COUNTERS = {}
            for row_index in range(1, sheet.nrows):
                excel_row = row_index + 1
                default_code = str(sheet.cell(row_index, DEFAULT_CODE).value)

                pk = default_code
                if not DEFAULT_CODE_COUNTERS.get(pk, False):
                    DEFAULT_CODE_COUNTERS[pk] = 0
                counter = DEFAULT_CODE_COUNTERS[pk] + 1
                if counter > 1:
                    raise ValidationError(
                        _("Solo puedes definir una vez un producto a la vez revisa el codigo %s ,fila %s") % (
                        default_code, excel_row))
                DEFAULT_CODE_COUNTERS[pk] = counter

                qty_value = sheet.cell(row_index, QUANTITY).value
                if type(qty_value) not in (int, float):
                    raise ValidationError(_("La cantidad debe ser numerica revisa la fila %s") % (excel_row,))
                quantity = int(qty_value)
                srch_product = OBJ_PRODUCT.search([('default_code', '=', default_code)])
                if not srch_product:
                    raise ValidationError(
                            _("No hay producto con codigo %s ,revisa la fila %s") % (default_code, excel_row))
                if len(srch_product) > 1:
                    raise ValidationError(
                            _("Existe mas de un producto con codigo %s en la base de datos ,revisa la fila %s") % (
                            default_code, excel_row))
                product=srch_product[0]
                move_ids_without_package.append((0, 0, {
                    "location_dest_id":   brw_each.movement_id.location_dest_id.id  ,
                    "location_id":  brw_each.movement_id.location_id.id ,
                    "product_id": product.id,
                    "product_uom_qty": quantity,
                    "name": product.name,                    #####
                    # "adjust_account_id": brw_each.account_id and brw_each.account_id.id or False,
                    # "adjust_partner_id": brw_each.partner_id and brw_each.partner_id.id or False,
                    # "adjust_id": brw_each.id,
                    # "adjust_line_id": brw_line.id,
                    # "property_stock_account_inventory_id": property_stock_account_inventory_id

                }))
                print(product.name, default_code, excel_row)
            brw_each.movement_id.write({"move_ids_without_package":move_ids_without_package})
        return True


class StockQuantHistoryWizard(models.TransientModel):
    _name = "stock.quant.history.wizard"
    _description = "Asistente para ver historial"

