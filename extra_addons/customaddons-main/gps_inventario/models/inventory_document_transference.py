# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from odoo import api, fields, models, _,SUPERUSER_ID

from odoo.exceptions import ValidationError, AccessError

class InventoryDocumentTransference(models.Model):
    _name="inventory.document.transference"
    _description="Transferencia de Inventario"
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _order="id desc"
    _check_company_auto = True

    @api.model
    def _get_default_uid(self):
        return [(6,0,[self._uid])]
    
    @api.model
    def _get_default_to_location_id(self):
        return False

    @api.model
    def _get_default_company_id(self):
        if self._context.get("allowed_company_ids",[]):
            return self._context.get("allowed_company_ids",[])[0]
        return False
    
    @api.model
    def _get_default_name(self):
        import pytz
        from datetime import datetime
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        display_date_result = datetime.strftime(pytz.utc.localize(fields.Datetime.now(),).astimezone(local),"%H:%M:%S") 
        
        return "TRANSFERENCIA %s" % (display_date_result ,)

    state=fields.Selection([('draft','Preliminar'),
                            ('revision','Revisado'),
                            ('started','Iniciado'),
                            ('ended','Finalizado'),
                            ('annulled','Anulado'),                            
                            ],default="draft",string="Estado",required=True, index=True, copy=False, tracking=True)

    company_id = fields.Many2one("res.company", string="Compañia", default=_get_default_company_id)
    line_ids=fields.One2many("inventory.document.transference.line","document_id","Detalle")
    user_ids=fields.Many2many("res.users","inventory_users_transference_rel","document_id","user_id","Responsable(s)",required=True,default=_get_default_uid)
    to_stock_location_id=fields.Many2one("stock.location",string="Ubicacion Destino",default=_get_default_to_location_id)
    
    picking_id=fields.Many2one("stock.picking","# Picking")
    returned_picking_id = fields.Many2one("stock.picking", "# Picking Retorno")
    confirmed_picking_id = fields.Many2one("stock.picking", "# Picking Confirmado")
    name = fields.Char("Referencia", required=True, copy=False, readonly=True, default="/")
    date_from=fields.Date(string="Fecha de Ajuste",required=True,default=fields.Date.today())
    stock_location_id=fields.Many2one("stock.location",string="Ubicacion Origen",required=True)
    document_type = fields.Selection([
        ('internal', 'Transferencia Interna'),
        ('dispatch', 'Despacho'),
    ], string="Tipo de Documento",default='internal', required=True)
    subcontratista_solicitante = fields.Many2one('res.partner','Subcontratista/Solicitante',required=False)
    intendente_solicitante = fields.Many2one('res.partner','Intendente/Residente',required=False)
    proyecto = fields.Char("Proyecto",required=True)
    warehouse_name = fields.Char("Nombre de Bodega", compute="_compute_warehouse_name", store=True)
    warehouse_name_dest = fields.Char("Nombre de Bodega", compute="_compute_warehouse_name_dest", store=True)

    @api.depends('stock_location_id')
    def _compute_warehouse_name(self):
        for rec in self:
            warehouse = self.env['stock.warehouse'].search([
                ('lot_stock_id', '=', rec.stock_location_id.id)
            ], limit=1)
            rec.warehouse_name = warehouse.name if warehouse else ''
    
    @api.depends('to_stock_location_id')
    def _compute_warehouse_name_dest(self):
        for rec in self:
            warehouse = self.env['stock.warehouse'].search([
                ('lot_stock_id', '=', rec.to_stock_location_id.id)
            ], limit=1)
            rec.warehouse_name_dest = warehouse.name if warehouse else ''

    # @api.onchange('document_type')
    # def _onchange_document_type(self):
    #     if self.state == 'draft' and not self.name:
    #         now_str = fields.Datetime.now().strftime("%H:%M:%S")
    #         prefix = "DESPACHO" if self.document_type == "dispatch" else "TRANSFERENCIA"
    #         self.name = "%s %s" % (prefix, now_str)

    #     warehouses = self.env.user.default_warehouse_ids
    #     allowed_locations = warehouses.mapped('lot_stock_id')

    #     if self.document_type == 'dispatch':
    #         if allowed_locations:
    #             self.stock_location_id = allowed_locations[0].id
    #             return {
    #                 'domain': {
    #                     'stock_location_id': [('id', 'in', allowed_locations.ids)],
    #                     'to_stock_location_id': []  # sin restricción
    #                 }
    #             }

    #     elif self.document_type == 'internal':
    #         if allowed_locations:
    #             self.to_stock_location_id = allowed_locations[0].id
    #             return {
    #                 'domain': {
    #                     'stock_location_id': [('usage', '=', 'internal')],
    #                     'to_stock_location_id': [('id', 'in', allowed_locations.ids)],
    #                 }
    #             }
    #         else:
    #             self.to_stock_location_id = False
    #             return {
    #                 'domain': {
    #                     'stock_location_id': [('usage', '=', 'internal')],
    #                     'to_stock_location_id': [('usage', '=', 'internal')],
    #                 }
    #             }
    @api.onchange('document_type')
    def _onchange_document_type(self):
        if self.state == 'draft' and not self.name:
            now_str = fields.Datetime.now().strftime("%H:%M:%S")
            prefix = "DESPACHO" if self.document_type == "dispatch" else "TRANSFERENCIA"
            self.name = "%s %s" % (prefix, now_str)

        user = self.env.user
        warehouses = user.default_warehouse_ids
        allowed_locations = warehouses.mapped('lot_stock_id')

        if self.document_type == 'dispatch':
            # Para despacho puede elegir libremente entre sus bodegas
            if allowed_locations:
                self.stock_location_id = False
                self.to_stock_location_id = False
                return {
                    'domain': {
                        'stock_location_id': [('id', 'in', allowed_locations.ids)],
                        'to_stock_location_id': [],
                    }
                }

        elif self.document_type == 'internal':
            if len(allowed_locations) == 1:
                self.stock_location_id = allowed_locations[0].id
                self.to_stock_location_id = False
                return {
                    'domain': {
                        'stock_location_id': [('id', '=', allowed_locations[0].id)],
                        'to_stock_location_id': [('usage', '=', 'internal')],
                    },
                    'warning': {
                        'title': _("Ubicación origen establecida"),
                        'message': _("Se asignó automáticamente la bodega asignada al usuario.")
                    }
                }
            elif len(allowed_locations) > 1:
                self.stock_location_id = False
                return {
                    'domain': {
                        'stock_location_id': [('id', 'in', allowed_locations.ids)],
                        'to_stock_location_id': [('usage', '=', 'internal')],
                    },
                    'warning': {
                        'title': _("Múltiples bodegas asignadas"),
                        'message': _("Selecciona la ubicación de origen entre las bodegas que tienes asignadas.")
                    }
                }
            else:
                self.stock_location_id = False
                return {
                    'warning': {
                        'title': _("Sin bodega asignada"),
                        'message': _("El usuario no tiene ninguna bodega predeterminada.")
                    }
                }
        
    @api.onchange('company_id')
    def onchange_company_id(self):
        self.stock_location_id = False
        self.to_stock_location_id=False
        self.line_ids=[(5,)]

    @api.onchange('stock_location_id','to_stock_location_id')
    def onchange_to_stock_location_id(self):
        if self.stock_location_id and self.to_stock_location_id:
            if self.stock_location_id==self.to_stock_location_id:
                self.to_stock_location_id=False
                return {"warning":{"title":_("Error"),
                                   "message":_("La ubicacion de origen y destino no puede ser la misma")
                                   }}
        self.line_ids=[(5,)]
            
        
    def action_update_stock(self):
        for brw_each in self:
            for brw_line in brw_each.line_ids:
                brw_line.update_stock()
        return True
    
    def action_start(self):
        for brw_each in self:
            if brw_each.to_stock_location_id==brw_each.stock_location_id:
                raise ValidationError(_("Las ubicaciones de origen y destino deben  ser diferentes"))
            if not brw_each.line_ids:
                raise ValidationError(_("No has definido ningun producto"))
            if not brw_each.company_id.transit_location_id:
                raise ValidationError(_("Debes configurar una bodega de transito para la empresa %s") % (brw_each.company_id.name,))
            for brw_line in brw_each.line_ids: 
                if brw_line.quantity<=0:
                    raise ValidationError(_("Todas las cantidades deben ser mayores a 0"))
                if brw_line.quantity_delivery<=0:
                    raise ValidationError(_("Todas las cantidades entregadas deben ser mayores a 0"))
                brw_line.update_stock()
                if brw_line.quantity_delivery>brw_line.quantity:
                    raise ValidationError(_("La cantidad entregada NO puede ser mayor al solicitado.%s contra %s") % (brw_line.quantity_delivery,brw_line.quantity))
                if brw_line.quantity>brw_line.stock:
                    raise ValidationError(_("La cantidad NO puede ser mayor al Stock.%s contra %s") % (brw_line.quantity,brw_line.stock))
                if brw_line.quantity_delivery>brw_line.stock:
                    raise ValidationError(_("La cantidad entregada NO puede ser mayor al Stock.%s contra %s") % (brw_line.quantity_delivery,brw_line.stock))
            brw_each.write({"state":"started"})
            brw_each.action_update_stock()
            brw_each.action_transference()
        return True
    
    def action_transference(self):
        OBJ_PICKING = self.env["stock.picking"]
        for brw_each in self:
            vals = {
                "picking_type_id": self._get_picking_type(
                    brw_each.company_id, brw_each.stock_location_id, origin_location="from", document_type=brw_each.document_type),
                "location_id": brw_each.stock_location_id.id,
                "location_dest_id": brw_each.company_id.transit_location_id.id,
                "origin": "TRANSFERENCIA %s" % (brw_each.id),
                'force_date': self.date_from,
                'analytic_distribution': self.analytic_distribution,
            }
            lines = [(5,)]
            for brw_line in brw_each.line_ids:
                if brw_line.quantity_delivery > 0:
                    if brw_line.quantity_delivery > brw_line.quantity:
                        raise ValidationError(_(
                            "No se puede entregar más cantidad (%s) de la solicitada (%s) para el producto %s." % (
                                brw_line.quantity_delivery, brw_line.quantity, brw_line.product_id.display_name)))

                    lines.append((0, 0, {
                        "location_id": brw_each.stock_location_id.id,
                        "location_dest_id": brw_each.company_id.transit_location_id.id,
                        "product_id": brw_line.product_id.id,
                        "product_uom_qty": brw_line.quantity_delivery,
                        "name": brw_line.name,
                        'analytic_distribution': brw_line.analytic_distribution,
                    }))
            if len(lines) == 0:
                raise ValidationError("No hay productos con cantidad entregada para transferir.")
            vals["move_ids_without_package"] = lines
            brw_picking = OBJ_PICKING.create(vals)
            brw_picking.action_confirm()
            for brw_line_move in brw_picking.move_ids_without_package:
                brw_line_move.write({"quantity_done": brw_line_move.product_uom_qty})
            brw_picking.button_validate()
            brw_each.picking_id = brw_picking.id
        return True


    def action_return(self):
        OBJ_PICKING = self.env["stock.picking"]
        for brw_each in self:
            vals = {
                "picking_type_id": self._get_picking_type(brw_each.company_id, brw_each.stock_location_id, origin_location="from", document_type=brw_each.document_type),
                "location_dest_id": brw_each.stock_location_id.id,
                "location_id": brw_each.company_id.transit_location_id.id,
                "origin": "RETORNO %s" % (brw_each.id),
                'force_date': self.date_from,
                "company_id": brw_each.company_id.id,  #
            }
            lines = [(5,)]
            for brw_line in brw_each.line_ids:
                if brw_line.quantity_delivery > 0:
                    quant = self.env['stock.quant'].search([
                        ('product_id', '=', brw_line.product_id.id),
                        ('location_id', '=', brw_each.company_id.transit_location_id.id)
                    ], limit=1)

                    if not quant or quant.quantity < brw_line.quantity_delivery:
                        raise ValidationError(_("No hay suficiente stock en tránsito para devolver el producto %s. Actualmente hay %s y se intenta devolver %s.") % (
                            brw_line.product_id.display_name,
                            quant.quantity if quant else 0.0,
                            brw_line.quantity_delivery))

                    lines.append((0, 0, {
                        "location_dest_id": brw_each.stock_location_id.id,
                        "location_id": brw_each.company_id.transit_location_id.id,
                        "product_id": brw_line.product_id.id,
                        "product_uom_qty": brw_line.quantity_delivery,
                        "name": brw_line.name
                    }))
            if len(lines) == 1:
                raise ValidationError(_("No hay productos con cantidad entregada para devolver."))
            vals["move_ids_without_package"] = lines
            brw_picking = OBJ_PICKING.create(vals)
            brw_picking.action_confirm()
            for brw_line_move in brw_picking.move_ids_without_package:
                brw_line_move.write({"quantity_done": brw_line_move.product_uom_qty})
            brw_picking.button_validate()
            brw_each.returned_picking_id = brw_picking.id
        return True

    def action_confirm(self):
        OBJ_PICKING=self.env["stock.picking"]
        for brw_each in self:
            vals={"picking_type_id":self._get_picking_type(brw_each.company_id, brw_each.stock_location_id, origin_location="from", document_type=brw_each.document_type),
                  "location_dest_id":brw_each.to_stock_location_id.id,
                  "location_id":brw_each.company_id.transit_location_id.id,
                  "origin":"CONFIRMACION %s" % (brw_each.id),
                  'force_date':self.date_from,
                  "company_id": brw_each.company_id.id,  #
                  }
            lines=[(5,)]
            for brw_line in brw_each.line_ids:
                lines.append((0,0,{
                    "location_dest_id":brw_each.to_stock_location_id.id,
                    "location_id":brw_each.company_id.transit_location_id.id,
                    "product_id":brw_line.product_id.id,
                    "product_uom_qty":brw_line.quantity,
                    "name":brw_line.name
                    }))
            vals["move_ids_without_package"]=lines
            brw_picking=OBJ_PICKING.create(vals)
            brw_picking.action_confirm()
            for brw_line_move in brw_picking.move_ids_without_package:
                brw_line_move.write({"quantity_done":brw_line_move.product_uom_qty})
            brw_picking.button_validate()
            brw_each.confirmed_picking_id=brw_picking.id
        return True

    @api.model
    def _where_calc(self, domain, active_test=True):
        if not domain:
            domain=[]
        return super(InventoryDocumentTransference,self)._where_calc(domain, active_test)
    
    @api.model
    def _get_default_location_id(self):
        return False
    
    
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
            brw_each.action_return()
            brw_each.write({"state":"annulled"})
        return True
    
    def action_revision(self):
        if not self.env.user.has_group('gps_inventario.group_ajuste_inventario_supervisor'):
            raise AccessError("Solo los usuarios supervisores/redisentes son los que pueden cambiar a revisado.")
        for brw_each in self:
            brw_each.write({"state":"revision"})
        return True
    
    def action_end(self):
        for brw_each in self:
            # Validar si debe generar confirmación (sólo si hay ubicación destino)
            if brw_each.document_type == 'internal':
                if not brw_each.to_stock_location_id:
                    raise ValidationError(_("No se ha definido una ubicación destino para la confirmación."))
                brw_each.action_confirm()
            # Cambiar el estado
            brw_each.write({"state": "ended"})
        return True
    
    def copy(self, default=None):
        raise ValidationError(_("Esta opcion no es valida para este documento"))


    def unlink(self):
        for brw_each in self:
            if self._context.get("validate_unlink", True):
                if brw_each.state != 'draft':
                    raise ValidationError(_("No puedes borrar un registro que no sea preliminar"))
        return super(InventoryDocumentTransference, self).unlink()

    @api.model
    def _get_picking_type(self, brw_company, brw_location_id, origin_location="from", document_type='internal'):
        field_location = "default_location_src_id"
        if origin_location != "from":
            field_location = "default_location_dest_id"
        picking_code = 'internal' if document_type == 'internal' else 'outgoing'
        srch = self.env["stock.picking.type"].with_context(force_company=brw_company.id).sudo().search([
            ('code', '=', picking_code),
            ('company_id', '=', brw_company.id),
            (field_location, '=', brw_location_id.id)
        ])
        if not srch:
            raise ValidationError(_("No existe tipo de operación %s para la ubicación %s") % (picking_code, brw_location_id.name))
        return srch[0].id
    
    @api.model
    def create(self, vals):
        if not vals.get("name"):
            vals["name"] = self.env['ir.sequence'].next_by_code('inventory.document.transference') or '/'
        return super(InventoryDocumentTransference, self).create(vals)

    def write(self, vals):
        if 'document_type' in vals and not self.name:
            now_str = fields.Datetime.now().strftime("%H:%M:%S")
            prefix = "DESPACHO" if vals['document_type'] == "dispatch" else "TRANSFERENCIA"
            vals["name"] = "%s %s" % (prefix, now_str)
        return super(InventoryDocumentTransference, self).write(vals)

    
    