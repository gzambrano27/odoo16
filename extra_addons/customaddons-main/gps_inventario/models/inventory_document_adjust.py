# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _,SUPERUSER_ID
from odoo.exceptions import ValidationError
import base64
import xlsxwriter
import io

class InventoryDocumentAdjustReport(models.AbstractModel):
    _name = 'report.gps_inventario.report_inventory_adjust'
    _description = 'Ajuste de Inventario Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['inventory.document.adjust'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'inventory.document.adjust',
            'doc': docs[0] if docs else None,  # Asegúrate de pasar `doc`
            'docs': docs,  # Alternativamente, usa `docs` para múltiples registros
        }
    

class InventoryDocumentAdjust(models.Model):
    _name="inventory.document.adjust"
    _description="Ajuste de Inventario"

    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    _check_company_auto = True
    
    @api.model
    def _get_default_uid(self):
        return [(6,0,[self._uid])]
    
    @api.model
    def _get_default_partner_id(self):
        return self.env["res.users"].browse(self._uid).company_id.partner_id.id
    
    @api.model
    def _get_default_company_id(self):
        return self.env["res.users"].browse(self._uid).company_id.id
    
    
    @api.model
    def _get_selection_state(self):
        return [('draft','Preliminar'),
                            ('started','Iniciado'),
                            ('ended','Finalizado'),
                            ('applied','Inventario Ajustado'),
                            ('annulled','Anulado'),                            
                            ]
    
    @api.model
    def _get_default_location_id(self):
        return False

    state=fields.Selection(selection=_get_selection_state,default="draft",string="Estado",required=True,tracking=True)
    line_ids=fields.One2many("inventory.document.adjust.line","document_id","Detalle")
    product_ids=fields.Many2many("product.product","inventory_product_adjust_rel","document_id","product_id","Producto(s)",required=True, domain=[('detailed_type','=','product')],tracking=True)
    user_ids=fields.Many2many("res.users","inventory_users_adjust_rel","document_id","user_id","Responsable(s)",required=True,default=_get_default_uid)
    name=fields.Char("Descripcion",required=True)
    date_from=fields.Date(string="Fecha de Ajuste",required=True,default=fields.Date.today(),tracking=True)
    stock_location_id=fields.Many2one("stock.location",string="Ubicacion Origen",required=True,default=_get_default_location_id)
    company_id=fields.Many2one("res.company",string="Compañia",default=lambda self: self.env.company)
    currency_id=fields.Many2one(related="company_id.currency_id",store=False,readonly=True)
    account_id=fields.Many2one("account.account",string="Cuenta Contable",tracking=True)
    partner_id=fields.Many2one("res.partner",string="Contacto",default=_get_default_partner_id,tracking=True)
    company_mult_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string='User',  store=True, default=lambda self: self.env.uid, readonly=True)

    attachment_ids=fields.Many2many("ir.attachment","inventory_adjust_attachment_rel","adjust_id","attachment_ids","Adjuntos")
    file_data = fields.Binary(string="Archivo Excel", readonly=True)

    picking_in_id=fields.Many2one("stock.picking","Picking Excedente")
    picking_out_id = fields.Many2one("stock.picking", "Picking Faltante")

    count=fields.Integer("# Lineas",compute="_get_compute_count",store=True,readonly=True)
    count_adjust = fields.Integer("# Ajustes", compute="_get_compute_count", store=True, readonly=True)
    count_adjust_in = fields.Integer("# Excedentes", compute="_get_compute_count", store=True, readonly=True)
    count_adjust_out = fields.Integer("# Faltantes", compute="_get_compute_count", store=True, readonly=True)
    count_equal = fields.Integer("# Cuadrados", compute="_get_compute_count", store=True, readonly=True)

    total_adjust_in = fields.Monetary("Excedentes", compute="_get_compute_count", store=True, readonly=True)
    total_adjust_out = fields.Monetary("Faltantes", compute="_get_compute_count", store=True, readonly=True)


    @api.depends('state','line_ids','line_ids.apply','line_ids.adjust')
    @api.onchange('state','line_ids','line_ids.apply','line_ids.adjust')
    def _get_compute_count(self):
        for brw_each in  self:
            brw_each.count=len(brw_each.line_ids)
            brw_each.count_adjust = (brw_each.state=='annulled') and 0 or len(brw_each.line_ids.filtered(lambda x: x.apply and x.adjust!=0.00))
            brw_each.count_adjust_in = (brw_each.state == 'annulled') and 0 or len(
                brw_each.line_ids.filtered(lambda x: x.apply and x.adjust > 0.00))
            brw_each.count_adjust_out = (brw_each.state == 'annulled') and 0 or len(
                brw_each.line_ids.filtered(lambda x: x.apply and x.adjust < 0.00))
            brw_each.count_equal = brw_each.count-brw_each.count_adjust

            brw_each.total_adjust_in = (brw_each.state == 'annulled') and 0 or sum(
                brw_each.line_ids.filtered(lambda x: x.apply and x.adjust > 0.00).mapped('total_cost'))
            brw_each.total_adjust_out = (brw_each.state == 'annulled') and 0 or sum(
                brw_each.line_ids.filtered(lambda x: x.apply and x.adjust < 0.00).mapped('total_cost'))



    @api.onchange('company_id')
    def onchange_company_id(self):
        self.stock_location_id = False
        self.line_ids = [(5,)]

    @api.onchange('stock_location_id')
    def onchange_stock_location_id(self):
        self.line_ids = [(5,)]

    def action_restart(self):
        for brw_each in self:
            brw_each.write({"state":"started"})
            brw_each.action_update_stock()
        return True
    
    def action_draft(self):
        for brw_each in self:
            brw_each.write({"state":"draft"})
        return True
    
    def action_cancel(self):
        for brw_each in self:
            brw_each.write({"state":"annulled"})
        return True
    
    def action_end(self):
        for brw_each in self:
            brw_each.write({"state":"ended"})
        return True
    
    def copy(self, default=None):
        raise ValidationError(_("Esta opcion no es valida para este documento"))

    def unlink(self):
        for brw_each in self:
            if self._context.get("validate_unlink", True):
                if brw_each.state != 'draft':
                    raise ValidationError(_("No puedes borrar un registro que no sea preliminar"))
        return super(InventoryDocumentAdjust, self).unlink()

    def action_update_stock(self):
        for brw_each in self:
            for brw_line in brw_each.line_ids:
                brw_line.update_stock()
        return True
    
    def action_start(self):
        for brw_each in self:
            if not brw_each.product_ids:
                raise ValidationError(_("No has definido ningun producto"))
            line_ids=[(5,)]
            quants = self._get_quants()
            for brw_quant in quants:#
                line_ids.append((0,0,{
                    "stock_location_id":brw_quant.location_id.id,
                    "product_id":brw_quant.product_id.id,
                    "name":brw_quant.product_id.name,
                    "stock":0,
                    "quantity":0,
                    "adjust":0,
                    "apply":True,
                    "comments":None
                }))
            brw_each.write({"state":"started","line_ids":line_ids})
            brw_each.action_update_stock()
        return True

    def get_all_locations(self):
        OBJ_LOCATION = self.env["stock.location"].sudo()
        locations = OBJ_LOCATION.search([
            ('usage', '=', 'internal'),  # Solo ubicaciones internas
            '|', ('id', '=', self.stock_location_id.id),  # Ubicaciones sin hijas
            ('location_id', '=', self.stock_location_id.id)
        ])
        return locations

    def _get_quants(self):
        locations = self.get_all_locations()
        location_ids = locations and locations.ids or []
        location_ids += [-1, -1]
        quants = self.env['stock.quant'].search([
            ('location_id', 'in', location_ids),
            ('quantity', '>', 0)
        ])
        return quants

    @api.onchange('stock_location_id')
    def onchange_stock_location_id(self):
        """
        Actualiza el dominio de `product_ids` con base en la ubicación seleccionada.
        """
        OBJ_LOCATION=self.env["stock.location"].sudo()
        self.line_ids = [(5,)]  # Limpia las líneas al cambiar la ubicación
        if self.stock_location_id:
            # Busca productos disponibles en la ubicación seleccionada

            quants = self._get_quants()
            product_ids = quants.mapped('product_id').ids

            # Actualiza el dominio para mostrar solo productos disponibles
            return {
                'domain': {
                    'product_ids': [('id', 'in', product_ids)],
                }
            }
        else:
            # Si no hay ubicación, elimina cualquier restricción de dominio
            return {
                'domain': {
                    'product_ids': [],
                }
            }

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

    def action_adjust_picking(self):
        DEC = 2
        OBJ_PICKING = self.env["stock.picking"].sudo()
        for brw_each in self:
            brw_each._get_compute_count()
            if not brw_each.account_id:
                raise ValidationError(_("Debes definir una cuenta"))
            if not brw_each.partner_id:
                raise ValidationError(_("Debes definir un contacto"))
            virtual_location_id=self._get_virtual_location_id()
            pickings={
                        "picking_in_id":{
                            "picking_type_id": self._get_picking_type(brw_each.company_id, brw_each.stock_location_id, 'incoming'  ),
                            "location_dest_id": brw_each.stock_location_id.id,
                            "location_id": virtual_location_id,
                            "origin": "AJUSTE # %s" % (brw_each.id,),
                            "move_ids_without_package":[]
                        },
                        "picking_out_id": {
                            "picking_type_id": self._get_picking_type(brw_each.company_id, brw_each.stock_location_id, 'outgoing' ),
                            "location_id": brw_each.stock_location_id.id,
                            "location_dest_id": virtual_location_id,
                            "origin": "AJUSTE # %s" % (brw_each.id,),
                            "move_ids_without_package":[]
                        },
            }

            for brw_line in brw_each.line_ids:
                if brw_line.apply and round(brw_line.adjust,DEC)!=0.00:
                    picking_ky=round(brw_line.adjust,DEC)>0.00 and "picking_in_id" or "picking_out_id"
                    lines=pickings[picking_ky]["move_ids_without_package"]

                    accounts_data = brw_line.product_id.product_tmpl_id.get_product_accounts()

                    acc_valuation = accounts_data.get('stock_valuation', False)
                    property_stock_account_inventory_id=False
                    if acc_valuation:
                        property_stock_account_inventory_id = acc_valuation.id

                    lines.append((0, 0, {

                        "location_dest_id": round(brw_line.adjust,DEC)>0.00 and brw_line.stock_location_id.id or virtual_location_id,
                        "location_id":round(brw_line.adjust,DEC)<0.00 and brw_line.stock_location_id.id or virtual_location_id,

                        "product_id": brw_line.product_id.id,
                        "product_uom_qty": abs(brw_line.adjust),
                        "name": brw_line.product_id.name,
                        #####
                        "adjust_account_id": brw_each.account_id and brw_each.account_id.id or False,
                        "adjust_partner_id": brw_each.partner_id and brw_each.partner_id.id or False,
                        "adjust_id": brw_each.id,
                        "adjust_line_id": brw_line.id,
                        "property_stock_account_inventory_id": property_stock_account_inventory_id

                    }))
                    pickings[picking_ky]["move_ids_without_package"]=lines

            for picking_ky in pickings:
                lines=pickings[picking_ky]["move_ids_without_package"]
                if lines:
                    vals=  pickings[picking_ky].copy()
                    brw_picking = OBJ_PICKING.create(vals)
                    brw_picking.action_confirm()
                    for brw_line_move in brw_picking.move_ids_without_package:

                        accounts_data = brw_line_move.product_id.product_tmpl_id.get_product_accounts()

                        acc_valuation = accounts_data.get('stock_valuation', False)
                        property_stock_account_inventory_id = False
                        if acc_valuation:
                            property_stock_account_inventory_id = acc_valuation.id

                        brw_line_move.write({"quantity_done": brw_line_move.product_uom_qty,
                                             "property_stock_account_inventory_id":property_stock_account_inventory_id
                                             })
                    brw_picking.button_validate()
                    brw_each.write({picking_ky: brw_picking.id})

            brw_each.update_account_move_line()
            brw_each.write({"state":"applied"})
        return True

    def action_adjust(self):
        DEC=2
        sup=self.env["res.users"].browse(SUPERUSER_ID)
        OBJ_QUANT=self.env["stock.quant"].sudo().with_user(sup)
        for brw_each in self:
            if not brw_each.account_id:
                raise ValidationError(_("Debes definir una cuenta"))
            if not brw_each.partner_id:
                raise ValidationError(_("Debes definir un contacto"))
            for brw_line in brw_each.line_ids:
                if brw_line.apply and round(brw_line.adjust,DEC)!=0.00:
                    srch_quant=OBJ_QUANT.search([('product_id','=',brw_line.product_id.id),
                                                 ('location_id','=',brw_line.stock_location_id.id)
                                                 ])
                    if not srch_quant:
                        srch_quant=OBJ_QUANT.create({'product_id':brw_line.product_id.id,
                                                     'location_id':brw_line.stock_location_id.id,
                                                     })
                    srch_quant.write({
                        "inventory_quantity":brw_line.quantity
                    })
                    srch_quant.with_user(sup)
                    
                    #aqui esta el cambio debe ser que reconozca en que compania estoy logeado
                    current_company = self.company_mult_id
                    if current_company:
                        company = self.env['res.company'].browse(current_company)
                    #property_stock_account_inventory_id=brw_line.product_id.with_company(brw_each.company_id).property_stock_inventory
                    property_stock_account_inventory_id=brw_line.product_id.with_company(current_company).property_stock_inventory
                    #brw_line = brw_line.with_company(brw_each.company_id)
                    brw_line = brw_line.with_company(current_company)
                    accounts_data = brw_line.product_id.product_tmpl_id.get_product_accounts()
                    
                    acc_valuation = accounts_data.get('stock_valuation', False)
                    if property_stock_account_inventory_id:
                        property_stock_account_inventory_id = acc_valuation.id
                    #aumentado
                    account_debit = accounts_data.get('stock_input', False)
                    account_credit = accounts_data.get('stock_output', False)
            
                    srch_quant=srch_quant.with_context({"acct_account_id":brw_each.account_id and brw_each.account_id.id or False,
                                                        "acct_partner_id":brw_each.partner_id and brw_each.partner_id.id or False,
                                                        "acct_adjust_id":brw_each.id,
                                                        "acct_adjust_line_id":brw_line.id,
                                                        "acct_property_stock_account_inventory_id":property_stock_account_inventory_id                                                        
                                                        })
                    srch_quant.action_apply_inventory()
            brw_each.update_account_move_line()
            brw_each.write({"state":"applied"})
        return True

    def update_account_move_line(self):
        brw_each=self.ensure_one()
        srch_move = self.env["stock.move"].sudo().search([('adjust_id', '=', brw_each.id)])
        for brw_move in srch_move:
            property_stock_account_inventory_id=brw_move.property_stock_account_inventory_id\
                                                and brw_move.property_stock_account_inventory_id.id or False
            for brw_account_move in brw_move.account_move_ids:
                for brw_move_line in brw_account_move.line_ids:
                    if brw_move_line.account_id.id != property_stock_account_inventory_id:
                        vals = {

                        }
                        # vals["account_id"]=2181#brw_each.account_id.id

                        if brw_move_line.debit > 0:
                            # brw_move_line.write({"account_id": account_debit.id})
                            vals["account_id"] = brw_each.account_id.id  # account_debit.id
                        elif brw_move_line.credit > 0:
                            # brw_move_line.write({"account_id": account_credit.id})
                            vals["account_id"] = brw_each.account_id.id  # account_credit.id

                        if brw_each.partner_id != brw_each.company_id.partner_id:
                            vals["partner_id"] = brw_each.partner_id.id
                        if vals:
                            brw_move_line._write(vals)
        return True

    def filter_movements(self):
        self.ensure_one()
        tree_id=self.env.ref("gps_inventario.inventory_document_adjust_line_view_tree_edit").id
        search_id = self.env.ref("gps_inventario.inventory_document_adjust_line_view_filter").id
        lst_ids=self.line_ids.ids
        lst_ids+=[-1,-1]
        return {
            'name': _("Ajuste de Inventario"),
            'view_mode': 'tree',
            'res_model': 'inventory.document.adjust.line',
            'type': 'ir.actions.act_window',
            'views': [(tree_id, 'tree'),(search_id, 'search')],
            'context': {},
            'domain':[('id','in',lst_ids)]
        }

    _order="id desc"


    def generate_excel_file(self):
        for record in self:
            # Crear el archivo Excel en memoria
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output)
            sheet = workbook.add_worksheet('Adjustments')

            # Formatos
            title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
            header_format = workbook.add_format({'bold': True, 'align': 'left'})
            value_format = workbook.add_format({'align': 'left'})

            # Cabecera principal
            #sheet.merge_range('A1:D1', record.company_id.name, title_format)
            sheet.write('A1', record.company_id.name, title_format)
            #sheet.merge_range('E1:H1', 'AJUSTE DE INVENTARIO', title_format)
            sheet.write('G1', 'AJUSTE DE INVENTARIO', title_format)

            # Detalles de la cabecera
            sheet.write('A2', 'FECHA DE INVENTARIO:', header_format)
            sheet.write('B2', str(record.date_from), value_format)

            sheet.write('A3', 'PRODUCTOS:', header_format)
            product_names = ','.join(record.product_ids.mapped('display_name'))
            #sheet.merge_range('B3:H3', product_names, value_format)
            sheet.write('B3', product_names, value_format)

            sheet.write('A4', 'UBICACION:', header_format)
            sheet.write('B4', record.stock_location_id.display_name, value_format)

            sheet.write('E2', '# LINEAS:', header_format)
            sheet.write('F2', len(record.line_ids), value_format)

            sheet.write('E3', 'RESPONSABLES:', header_format)
            user_names = ','.join(record.user_ids.mapped('name'))
            #sheet.merge_range('F3:H3', user_names, value_format)
            sheet.write('F3', user_names, value_format)
            # Espaciado para la tabla
            row = 4
            # Encabezados de la tabla
            if self.env.user.has_group('gps_inventario.group_ajuste_inventario_manager') or self.env.user.has_group('gps_inventario.group_ajuste_inventario_costo_manager'):
                headers = ['#ID','Ubicación','Ref. Anterior','Ref. Interna','Nombre' , 'Cantidad', 'Comentario','Unidad Medida','Stock','Costo','Aplicar']
            else:
                headers = ['#ID','Ubicación','Ref. Anterior','Ref. Interna','Nombre' , 'Cantidad', 'Comentario','Unidad Medida','Aplicar']

            for col, header in enumerate(headers):
                sheet.write(row, col, header, header_format)
            row = row + 1
            for line in record.line_ids:
                sheet.write(row, 0, line.id)
                sheet.write(row, 1, line.stock_location_id.display_name or '')
                sheet.write(row, 2, line.product_id.referencia_anterior or '')
                sheet.write(row, 3, line.product_id.default_code or '')
                sheet.write(row, 4, line.product_id.name or '')
                sheet.write(row, 5, line.quantity)
                sheet.write(row, 6, line.comments or '')
                sheet.write(row, 7, line.product_id.uom_id.name or '')
                column=8
                if self.env.user.has_group('gps_inventario.group_ajuste_inventario_manager') or self.env.user.has_group('gps_inventario.group_ajuste_inventario_costo_manager'):
                    sheet.write(row, 8, line.stock or 0)
                    sheet.write(row, 9, line.standard_price or 0)
                    column=10
                sheet.write(row,column, line.apply and 'SI' or 'NO')
                row += 1

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