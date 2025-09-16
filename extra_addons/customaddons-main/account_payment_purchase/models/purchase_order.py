# -*- coding: utf-8 -*-
# © <2024> <Washington Guijarro>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tools.translate import _ as _t
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, time, timedelta
import logging
import xlsxwriter
import base64
from io import BytesIO
from datetime import datetime
import pytz
_logger = logging.getLogger(__name__)
import base64
import xlsxwriter
import io
import json
from odoo.exceptions import ValidationError
from collections import defaultdict

class ConfigSettingsUserApproval(models.Model):
    _name = 'config.settings.approval.po'
    
    usuario_id = fields.Many2one('res.users')
    monto_desde = fields.Float(string="Desde")
    monto_hasta = fields.Float(string="Hasta")
    approve_financiero = fields.Boolean('Requiere aprobacion', tracking = True)
    estado = fields.Selection([
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ], 'Estado', track_visibility='onchange', copy=False, default='activo')
    
class ConfigSettingsUserApprovalAdmin(models.Model):
    _name = 'config.settings.approval.po.admin'
    
    usuario_id = fields.Many2one('res.users')
    monto_desde = fields.Float(string="Desde")
    monto_hasta = fields.Float(string="Hasta")
    approve_financiero = fields.Boolean('Requiere aprobacion')
    estado = fields.Selection([
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ], 'Estado', track_visibility='onchange', copy=False, default='activo')
    usuario_creador = fields.Many2one('res.users')
    
class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.constrains('order_line')
    def _check_analytic_distribution(self):
        for record in self.order_line:
            if not record.analytic_distribution and not record.custom_requisition_line_id and record.product_id: 
                raise UserError(_("No puedes crear o modificar una orden de compra sin haber ingresado la distribución analítica."))
            
    @api.constrains('order_line', 'analytic_distribution')
    def _check_analytic_account_1(self):
        for order in self:
            # Verificar si existe cuenta analítica en la cabecera
            if order.origin:
                if 'PR' not in order.origin:
                    if not order.analytic_distribution and not any(line.analytic_distribution for line in order.order_line):
                        raise UserError("Debe asignar una cuenta analítica en la cabecera o en las líneas de la orden de compra.")
            else:
                if not order.analytic_distribution and not any(line.analytic_distribution for line in order.order_line):
                    raise UserError("Debe asignar una cuenta analítica en la cabecera o en las líneas de la orden de compra.")
    
    @api.constrains('order_line', 'analytic_distribution')
    def _check_analytic_account(self):
        for order in self:
            # Verificar si existe cuenta analítica en la cabecera
            if order.origin:
                if 'PR' not in order.origin:
                    if not order.analytic_distribution and not any(line.analytic_distribution for line in order.order_line):
                        raise UserError("Debe asignar una cuenta analítica en la cabecera o en las líneas de la orden de compra.")
            
            
    # @api.onchange('payment_term_id')
    # def _onchange_payment_term(self):
    #     if self.payment_term_id:
    #         payment_days = self.payment_term_id.line_ids.filtered(lambda l: l.days > 0)
    #         if payment_days:
    #             max_days = max(payment_days.mapped('days'))
    #             self.date_planned = fields.Date.context_today(self) + relativedelta(days=max_days)
    
    def _get_usuario_aprobacion(self, amount, es_admin):
        usuario_aprobacion = self.env.user.id
        requiere_aprobacion = False
        if es_admin:
            settings = self.env['config.settings.approval.po.admin'].search([('estado', '=', 'activo')])
        else:
            settings = self.env['config.settings.approval.po'].search([('estado', '=', 'activo')])
        usuario_temp = None  # Almacena un posible aprobador si aún no encuentra uno exacto

        for x in settings:
            if x.monto_desde <= amount <= x.monto_hasta:
                if not es_admin:  # Si no es admin, tomar la primera coincidencia
                    return x.usuario_id.id, x.approve_financiero
                else:  # Si es admin, verificar si el usuario que envía es el usuario creador
                    if self.env.user.id == x.usuario_creador.id or self.solicitante.id==x.usuario_creador.id:
                        return x.usuario_id.id, x.approve_financiero  # Se encontró el creador correcto
                    usuario_temp = (x.usuario_id.id, x.approve_financiero)  # Guardar un posible aprobador

        return usuario_temp if usuario_temp else (usuario_aprobacion, requiere_aprobacion)
        
            
    @api.onchange('order_line')
    def _onchange_order_line(self):
        self._amount_all()
        for order in self:
            if order.amount_untaxed:#order.amount_total:
                usuario_aprobacion, requiere_aprobacion = self._get_usuario_aprobacion(self.amount_untaxed, self.es_admin)#self.amount_total)
                _logger.info(f'Usuario aprobación: {usuario_aprobacion}, Requiere aprobación: {requiere_aprobacion}')
                order.usuario_aprobacion_id = usuario_aprobacion
                order.requiere_aprobacion = requiere_aprobacion

    def obtiene_amount(self,vals_list):
        subt = 0
        imp = 0
        for vals in vals_list:
            order_lines = vals.get('order_line', [])
            for line in order_lines:
                precio = line[2]['price_unit']*line[2]['product_qty'] - (line[2]['price_unit']*line[2]['product_qty'] *(line[2]['discount']/100 if line[2]['discount'] else 0))
                subtimp = 0
                if line[2]['taxes_id']:
                    taxes = line[2].get('tax_id', [])
                    for tax in line[2]['taxes_id']:
                        valimp = self.env['account.tax'].browse(tax[2]).amount
                        subtimp += precio + ( precio * valimp/100)
                else:   
                    subtimp = precio        
                subt += subtimp
        return subt
                
                
    @api.model_create_multi
    def create(self, vals_list):
        #verifico el proveedor y los productos
        # if not self.env['res.partner'].browse(vals_list[0]['partner_id']).verificado:
        #     raise UserError(_("No puedes registrar una orden de compra para un proveedor que no  ha sido verificado!!!"))
        try:
            self._check_analytic_account()
            if not 'EPR' in vals_list[0]['origin']:
                if vals_list[0]['order_line']:
                    for x in vals_list[0]['order_line']:
                        if not self.env['product.product'].browse(x[2]['product_id']).verificado and x[2]['product_qty']>0:
                            raise UserError(_("No puedes registrar una orden de compra para un producto que no  ha sido verificado %s!!!")%(self.env['product.product'].browse(x[2]['product_id']).name))
                valor = self.obtiene_amount(vals_list)
                _logger.info(valor)
                es_admin = False
                for vals in vals_list:
                    es_admin = vals.get('es_admin')
                usuario_aprobacion, requiere_aprobacion = self._get_usuario_aprobacion(valor, es_admin)
                vals = []
                for vals in vals_list:  
                    vals['usuario_aprobacion_id'] = usuario_aprobacion
                    vals['requiere_aprobacion'] = requiere_aprobacion
        except:
            try:
                if vals_list[0]['order_line']:
                        for x in vals_list[0]['order_line']:
                            if not self.env['product.product'].browse(x[2]['product_id']).verificado and x[2]['product_qty']>0:
                                raise UserError(_("No puedes registrar una orden de compra para un producto que no  ha sido verificado %s!!!")%(self.env['product.product'].browse(x[2]['product_id']).name))
                            valor = self.obtiene_amount(vals_list)
                            es_admin = False
                            for vals in vals_list:
                                es_admin = vals.get('es_admin')
                            _logger.info(valor)
                            usuario_aprobacion, requiere_aprobacion = self._get_usuario_aprobacion(valor,es_admin)
                            vals = []
                            for vals in vals_list:  
                                vals['usuario_aprobacion_id'] = usuario_aprobacion
                                vals['requiere_aprobacion'] = requiere_aprobacion 
            except:
                print('Error en la creacion de la orden de compra')   
        result = super(PurchaseOrder, self).create(vals_list)
        return result

    def write(self, vals):
        for x in self:
            if x.state in ['control_presupuesto', 'to approve', 'purchase', 'done', 'cancel']:
                allowed_fields = {'state',
                                  'file_data',
                                    'mail_reminder_confirmed',
                                    'activity_exception_decoration',
                                    'message_follower_ids',
                                    '__last_update',
                                    'message_needaction',
                                    'message_has_error',
                                    'message_has_error_counter',
                                    'date_planned',
                                    'date_approve',
                                    'usuario_aprobacion_id',
                                    'requiere_aprobacion',
                                    'es_admin',
                                    'is_developer',
                                    'is_editable',
                                    'es_presidencia',
                                    'payment_request_ids',
                                    'purchase_payment_line_ids',
                                    'total_payments_advances',
                                    'total_dif_payments_advances',
                                    'validate_with_base_amount',
                                    'total_request_payments',
                                    'total_dif_request_payments',
                                    'warning_date_advance_payment_message',
                                    'warning_date_advance_payment',
                                    'overdue_days',
                                    'group_id',
                                    'partner_ref',
                                    'importation_id',
                                    'date_advance_first_payment',
                                    'date_advance_payment',
                                    'message_main_attachment_id',
                                    'priority',
                                    'order_line',
                                    'access_token',
                                    'base_precio_real',
                                    'margen_bruto_gen',
                                    'margen_bruto_sin_dscto',
                                    'state_confirmed',
                                    'analytic_distribution',
                                    'state', 
                                    'usuario_approve'
                                }
                incoming_fields = set(vals.keys())
                if not incoming_fields.issubset(allowed_fields):
                    raise UserError("No puedes modificar una orden de compra en estado '%s'." % x.state)
                # Si se está modificando `order_line`, validar los campos permitidos dentro de las líneas
                if 'order_line' in vals:
                    for command in vals['order_line']:
                        if isinstance(command, (list, tuple)) and len(command) >= 3 and isinstance(command[2], dict):
                            line_vals = command[2]
                            allowed_line_fields = {'taxes_id','employees_ids','margen','precio_real','margen_con_dscto','descuento_presupuesto','qty_received_manual','qty_received','rubro', 'precio_venta', 'tipo_costo_id','date_planned','wa_line_ids','qty_accepted','qty_to_accept',}
                            line_id = self.env['purchase.order.line'].browse(command[1]) if command[0] == 1 else None

                            for field_name, new_value in line_vals.items():
                                if field_name not in allowed_line_fields:
                                    if not line_id:
                                        raise UserError(f"No se permite modificar el campo '{field_name}' en estado bloqueado.")
                                    current_value = line_id[field_name]
                                    if hasattr(current_value, 'id'):
                                        current_value = current_value.id
                                    if current_value != new_value:
                                        raise UserError(f"No se permite modificar el campo '{field_name}' en estado bloqueado.")
            vals, partner_vals = x._write_partner_values(vals)
            _logger.info(vals)
            _logger.info(x.amount_untaxed)
            x._check_analytic_account()
            user = x.env.user  # Obtiene el usuario actual
            user_groups = user.groups_id  # Devuelve los grupos del usuario
            band_app = 0
            for group in user_groups:
                if group.name == 'Financiero Aprobador':
                    band_app = 1
            #se agrega valores de logica de aprobadores
            if band_app == 0 and 'amount_untaxed' in vals:
                usuario_aprobacion, requiere_aprobacion = x._get_usuario_aprobacion(x.amount_untaxed, (x.es_admin or x.es_presidencia))#self.amount_total)
                vals['usuario_aprobacion_id'] = usuario_aprobacion
                vals['requiere_aprobacion'] = requiere_aprobacion
            res = super().write(vals)
            if partner_vals:
                x.partner_id.sudo().write(partner_vals)  # Because the purchase user doesn't have write on `res.partner`
            return res
    
    @api.depends('state', 'usuario_aprobacion_id', 'amount_untaxed')#'amount_total')
    def _compute_show_approve_button(self):
        for order in self:
            if order.state == 'to approve' and order.usuario_aprobacion_id == self.env.user:
                order.show_approve_button = True
            else:
                order.show_approve_button = False
    
    file_data = fields.Binary(string="Archivo Excel", readonly=True)
    solicitante = fields.Many2one('res.users', 'Solicitante',default=False)
    show_approve_button = fields.Boolean(string='Mostrar botón de Aprobar', compute='_compute_show_approve_button', store=True)
    usuario_aprobacion_id = fields.Many2one('res.users', string='Usuario de Aprobación', states={'approved': [('readonly', True)], 'done': [('readonly', True)]},default=False)
    requiere_aprobacion = fields.Boolean(string='Aprobar Financiero',default=False, tracking=True)
    importacion = fields.Boolean(string='Es Importacion?',default=False)
    orden_compra_anterior = fields.Char(string='Orden de Compra Anterior')
    sale_order_id = fields.Many2one('sale.order','Pedido de Venta')
    referencia_analitica = fields.Char(related = 'sale_order_id.referencia_analitica',string='Referencia Analitica')       
    fecha_llegada_inventario = fields.Date(string='Fecha de Llegada de Inventario')
    es_admin = fields.Boolean(string='Es Orden Administrativa',default=False)
    es_presidencia = fields.Boolean(string='Es Orden Presidencia',default=False)
    is_developer = fields.Boolean(
        compute='_compute_is_developer',
        store=True
    )
    is_editable = fields.Boolean(
        string='¿Es editable?',
        compute='_compute_is_editable',
    )

    lead_time = fields.Integer(string='Lead Time')
    costo_gen = fields.Float('Costo', compute='_compute_base_general', store = True)
    base_precio_real = fields.Float('P. Real Gen', compute='_compute_base_general', store = True)
    margen_bruto_sin_dscto = fields.Float('M. Bruto Sin Dscto', compute='_compute_base_general', store = True)
    margen_bruto_gen = fields.Float('M. Bruto Gen', compute='_compute_base_general', store = True)
    prioridad_orden = fields.Selection([
        ('alta', 'Alta'),
        ('media', 'Media'),
        ('baja', 'Baja')
        ], 'Prioridad Orden', default='alta')
    prioridad_color = fields.Char(compute='_compute_prioridad_color')
    meta_descuento = fields.Float('Meta con Dscto', compute='_compute_base_general', store = True)
    ahorro_meta = fields.Float('Ahorro', compute='_compute_base_general', store = True)
    date_confirm_control = fields.Datetime('Confirmation Control', readonly=1, index=True, copy=False)
    usuario_approve = fields.Many2one('res.users', string="Usuario aprobador", readonly=True, tracking=True)

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        if not self.sale_order_id:
            return

        # Limpiar líneas actuales
        self.order_line = [(5, 0, 0)]

        sale_order = self.sale_order_id
        lines = []

        for sol in sale_order.order_line:
            vals = {
                'product_id': sol.product_id.id,
                'name': sol.name,
                'product_qty': sol.product_uom_qty,
                'product_uom': sol.product_uom.id,
                'price_unit': sol.price_unit,
                'taxes_id': [(6, 0, sol.tax_id.ids)],
                'discount': sol.discount,
                'date_planned': fields.Date.today(),
            }
            lines.append((0, 0, vals))

        self.order_line = lines
        
    @api.depends('prioridad_orden')
    def _compute_prioridad_color(self):
        for line in self:
            margin_type = 'margen-apu-cab'  # Tipo de margen a evaluar
            color = line.prioridad_orden
            
            # Mapear valores de color a opciones válidas
            mapping = {
                'baja': 'verde',
                'media': 'naranja',
                'alta': 'rojo'
            }
            line.prioridad_color = mapping.get(color, 'rojo')  # Valor predeterminado es 'rojo'

    @api.depends('order_line.subtotal_precio_real', 'order_line.price_subtotal','order_line.precio_venta', 'amount_total', 'amount_untaxed')
    def _compute_base_general(self):
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            subtotal_precio_real_gen = sum(order_lines.mapped('subtotal_precio_real'))
            subtotal_precio_vta_gen = sum(order_lines.mapped('precio_venta'))
            # Filtrar líneas con precio de venta definido (> 0)
            lines_with_precio_venta = order_lines.filtered(lambda l: l.precio_venta > 0)
            subtotal_precio_gen = sum(lines_with_precio_venta.mapped('price_subtotal'))
            subtotal_precio_sin_dscto = sum(order_lines.mapped('subtotal_precio_sin_dscto'))
            order.base_precio_real = subtotal_precio_real_gen
            order.meta_descuento = subtotal_precio_real_gen * 0.75
            order.ahorro_meta = (subtotal_precio_real_gen * 0.75) - order.amount_untaxed
            if subtotal_precio_real_gen > 0:
                order.margen_bruto_gen = 1 - (subtotal_precio_gen / subtotal_precio_real_gen)
                order.costo_gen = subtotal_precio_gen
                order.margen_bruto_sin_dscto = 1 - (subtotal_precio_gen /subtotal_precio_sin_dscto)
            else:
                order.margen_bruto_gen = 0.0
                order.margen_bruto_sin_dscto =  0.0
                order.costo_gen =  0.0

    @api.depends('state')
    def _compute_is_editable(self):
        for record in self:
            record.is_editable = record.state not in [
                'control_presupuesto', 'to approve', 'purchase', 'done', 'cancel'
            ]

    @api.constrains('lead_time')
    def _check_lead_time_positive(self):
        for record in self:
            if record.purchase_order_type != 'service' and record.lead_time <= 0:
                raise ValidationError("El Lead Time debe ser mayor a 0.")
            #if record.purchase_order_type == 'service':
            #    self.lead_time = 0

    def _compute_is_developer(self):
        for rec in self:
            rec.is_developer = self.env.context.get('debug', False)

    def copy(self, default=None):
        # Si no se especifica un diccionario 'default', creamos uno vacío
        if default is None:
            default = {}

        # Llamar al método original para crear la copia
        new_record = super(PurchaseOrder, self).copy(default)

        # Limpiar los campos personalizados en la copia después de crearla
        new_record.write({
            'solicitante': False,  # Reemplaza con el nombre del campo personalizado
            'usuario_aprobacion_id': False,  # Reemplaza con el nombre del campo personalizado
            'requiere_aprobacion': False,  # Reemplaza con el nombre del campo personalizado
            'importacion': False,  # Reemplaza con el nombre del campo personalizado
        })

        # Devolver el nuevo registro creado con los campos personalizados vacíos
        return new_record
    
    def button_approve(self, force=False):
        if self.company_id.id != 1 or self.partner_id.id not in (11, 39, 12, 13):
            self = self.filtered(lambda order: order._approval_allowed())
            
            # if self.requiere_aprobacion:
            #     raise UserError(_("No puedes aprobar una orden de compra que no ha sido verificada por Financiero!!!"))
            
            settings_model = 'config.settings.approval.po.admin' if self.es_admin or self.es_presidencia else 'config.settings.approval.po'
            settings = self.env[settings_model].search([('estado', '=', 'activo')])
            usuario_aprobacion = None
            usuario_aprobacion,requiere_aprobacion = self._get_usuario_aprobacion(self.amount_untaxed, (self.es_admin or self.es_presidencia))
            
            # for config in settings:
            #     if config.monto_desde <= self.amount_untaxed <= config.monto_hasta and config.usuario_id.id == self.env.user.id:
            #         usuario_aprobacion = config.usuario_id.id
            #         break
            
            if usuario_aprobacion is None:
                for config in settings:
                    if config.monto_desde <= self.amount_untaxed <= config.monto_hasta:
                        usuario_aprobacion = config.usuario_id.id
                        break
            
            if usuario_aprobacion and usuario_aprobacion != self.env.user.id:
                user_check = self.env[settings_model].search([
                    ('estado', '=', 'activo'),
                    ('usuario_id', '=', self.env.user.id),
                    ('monto_desde', '>=', self.amount_untaxed)
                ])
                
                if not user_check:
                    if self.amount_total > 0:
                        raise UserError(_t(
                            "No puedes aprobar una orden de compra ya que no eres el usuario aprobador %s!!!"
                        ) % str(self.env['res.users'].browse(usuario_aprobacion).name))
            
            fecha_aprobacion = fields.Datetime.now()
            
            #if self.date_planned and self.date_planned.date() < fecha_aprobacion.date():
            #    dias_diferencia = (fecha_aprobacion.date() - self.date_planned.date()).days
            dias_diferencia = 0
            if self.purchase_order_type != 'service' and not self.lead_time <= 0:
                dias_diferencia = self.lead_time
            #    self.date_planned = self.date_planned + timedelta(days=dias_diferencia)
                self.date_planned = fecha_aprobacion + timedelta(days=dias_diferencia)

                for line in self.order_line:
                    #if line.date_planned and line.date_planned.date() < fecha_aprobacion.date():
                    #    line.date_planned = line.date_planned + timedelta(days=dias_diferencia)
                    if line.date_planned:
                        line.date_planned = fecha_aprobacion + timedelta(days=dias_diferencia)

            self.write({
                'state': 'purchase',
                'date_approve': fecha_aprobacion,
                'usuario_aprobacion_id': usuario_aprobacion,
                'usuario_approve':self.env.user.id
            })
            
            if self.company_id.po_lock == 'lock':
                self.write({'state': 'done'})
            
            if self.usuario_aprobacion_id.id != usuario_aprobacion and self.amount_total != 0:
                raise UserError(_(
                    "No puedes aprobar una orden de compra, el usuario aprobador debe ser %s!!!"
                ) % self.usuario_aprobacion_id.name)

            template = self.env.ref('account_payment_purchase.email_purchase_order_custom_new', raise_if_not_found=False)
            for order in self:
                if order.state in ('purchase', 'done') and template:
                    # 1) Obtener el action del reporte de OC (según tu Odoo puede variar el xmlid)
                    report_xmlid = False
                    for rid in ('purchase.action_report_purchase_order',
                                'purchase.action_report_purchaseorder'):
                        if self.env.ref(rid, raise_if_not_found=False):
                            report_xmlid = rid
                            break
                    if not report_xmlid:
                        raise UserError("No se encontró el reporte de Orden de Compra (verifica el xmlid en Depurador Técnico).")

                    # 2) Renderizar PDF en memoria
                    pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(report_xmlid, [order.id])

                    # 3) Crear adjunto
                    attach = self.env['ir.attachment'].create({
                        'name': f'OC_{order.name}.pdf',
                        'type': 'binary',
                        'datas': base64.b64encode(pdf_content),
                        'res_model': 'purchase.order',
                        'res_id': order.id,
                        'mimetype': 'application/pdf',
                    })

                    # 4) Enviar el correo inyectando el adjunto
                    #    (sin tocar attachment_ids de la plantilla para no “ensuciarla” globalmente)
                    email_vals = {'attachment_ids': [(6, 0, [attach.id])]}
                    template.sudo().send_mail(order.id, email_values=email_vals, force_send=True)
            # for order in self:
            #     if order.state in ('purchase', 'done') and template:
            #         template.sudo().send_mail(order.id, force_send=True)
        else:
            self.write({'state': 'purchase', 'date_approve': fields.Datetime.now()})
            if self.company_id.po_lock == 'lock':
                self.write({'state': 'done'})
        
        return super().button_approve(force)
    
    def _prepare_sale_order_data(
            self, name, partner, dest_company, direct_delivery_address
        ):
            new_order = super()._prepare_sale_order_data(
                name, partner, dest_company, direct_delivery_address
            )
            delivery_address = (
                direct_delivery_address
                or self.picking_type_id.warehouse_id.partner_id
                or False
            )
            if delivery_address:
                new_order.update({"partner_shipping_id": delivery_address.id})
            warehouse = (
                dest_company.warehouse_id.company_id == dest_company
                and dest_company.warehouse_id
                or False
            )
            if warehouse:
                new_order.update({"warehouse_id": warehouse.id})
            if self.analytic_distribution:
                id_analitico = next(iter(self.analytic_distribution))
                nombre = self.env['account.analytic.account'].browse(int(id_analitico)).name
                # Acceder correctamente a los IDs de los registros de Many2many
                #analytic_distribution_ids = self.analytic_distribution.ids
                new_order.update({"referencia_analitica": nombre}) #[(6, 0, analytic_distribution_ids)]})
            return new_order
    
    def _prepare_sale_order_line_data_cross(self, purchase_line, dest_company, sale_order):
        """Generate the Sale Order Line values from the PO line
        :param purchase_line : the origin Purchase Order Line
        :rtype purchase_line : purchase.order.line record
        :param dest_company : the company of the created SO
        :rtype dest_company : res.company record
        :param sale_order : the Sale Order
        """
        new_line = self.env["sale.order.line"].new(
            {
                "order_id": sale_order.id,
                "product_id": purchase_line.product_id.id,
                "product_uom": purchase_line.product_uom.id,
                "product_uom_qty": purchase_line.product_qty,
                "auto_purchase_line_id": purchase_line.id,
                "display_type": purchase_line.display_type,
                'analytic_distribution':purchase_line.analytic_distribution,
            }
        )
        for onchange_method in new_line._onchange_methods["product_id"]:
            onchange_method(new_line)
        new_line.update({"product_uom": purchase_line.product_uom.id})
        if new_line.display_type in ["line_section", "line_note"]:
            new_line.update({"name": purchase_line.name})
        return new_line._convert_to_write(new_line._cache)
    
    def button_cancel(self):
        if self.env.user.has_group('account_payment_purchase.group_purchase_user_registrador') and self.state=='purchase' and self.amount_total!=0:
            raise UserError(_("No tienes permiso para cancelar una orden de compra!!."))
        for order in self:
            for inv in order.invoice_ids:
                if inv and inv.state not in ('cancel', 'draft'):
                    raise UserError(_("Unable to cancel this purchase order. You must first cancel the related vendor bills."))

        self.write({'state': 'cancel', 'mail_reminder_confirmed': False})

    def button_draft(self):
        if self.env.user.has_group('account_payment_purchase.group_purchase_user_registrador') and self.state=='purchase':
            raise UserError(_("No tienes permiso para regesar una orden de compra a borrador!!."))
        self.write({'state': 'draft'})
        return {}

    def button_confirm(self):
        for order in self:
            order._check_analytic_account_1()
            order._check_analytic_distribution()
            if self.env.user.has_group('account_payment_purchase.group_purchase_user_registrador'):
                raise UserError(_("No tienes permiso para confirmar la solicitud de compra!!."))

            if order.state not in ['draft', 'sent']:
                continue
            order.order_line._validate_analytic_distribution()
            order._add_supplier_to_product()
            # Deal with double validation process
            if order._approval_allowed():
                #Logica para hacer la aprobacion de ordenes de compra
                usuario_aprobacion_id, requiere_aprobacion = self._get_usuario_aprobacion(self.amount_untaxed, (self.es_admin or self.es_presidencia))#self.amount_total)
                if requiere_aprobacion:
                    if self.requiere_aprobacion:
                        raise UserError(_("No puedes registrar una orden de compra que no ha sido verificada por Financiero!!!"))
                usuario_aprobacion = self.env.user.id
                requiere_aprobacion = False
                if self.es_admin:
                    settings = self.env['config.settings.approval.po.admin'].search([('estado','=','activo')])
                else:
                    settings = self.env['config.settings.approval.po'].search([('estado','=','activo')])
                for x in settings:
                    print (x.monto_desde)
                    #if x.monto_desde <= self.amount_total <= x.monto_hasta:
                    if x.monto_desde <= self.amount_untaxed <= x.monto_hasta and x.usuario_id.id==self.env.user.id:
                        usuario_aprobacion = x.usuario_id.id
                        #if usuario_aprobacion!=self.env.user.id and self.amount_total > x.monto_hasta:
                        if usuario_aprobacion!=self.env.user.id and self.amount_untaxed > x.monto_hasta:
                            #voy a buscar si el usuario diferente esta en la tabla de configuraciones
                            if self.es_admin:
                                if not self.env['config.settings.approval.po.admin'].search([('estado', '=', 'activo'),('usuario_id','=',self.env.user.id),('monto_desde','>=',self.amount_total)]):
                                    raise UserError(_("No puedes registrar una orden de compra que supera tu maximo de aprobacion, max permitido %s!!!")%(str(float(x.monto_hasta))))
                            if not self.es_admin:
                                if not self.env['config.settings.approval.po'].search([('estado', '=', 'activo'),('usuario_id','=',self.env.user.id),('monto_desde','>=',self.amount_total)]):
                                    raise UserError(_("No puedes registrar una orden de compra que supera tu maximo de aprobacion, max permitido %s!!!")%(str(float(x.monto_hasta))))
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
        return True
    
    def send_pending_approval_emails_aaviles(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        aprobadores = self.env['res.users'].search([('id', '=', 23)])

        for user in aprobadores:
            # Filtrar órdenes asignadas a ese aprobador
            orders = self.env['purchase.order'].search([
                ('state', '=', 'financiero')
            ])
            if not orders:
                continue

            table_rows = ""
            for order in orders:
                order = self.env['purchase.order'].browse(order.id)
                fecha_envio_cp = None  # Aquí se guardará la fecha del cambio a Control Presupuesto
                usuario_envio_cp = None
                mensajes = self.env['mail.message'].search([
                    ('model', '=', 'purchase.order'),
                    ('res_id', '=', order.id),
                    ('message_type', '=', 'notification')
                ], order='date asc')  # Aseguramos orden cronológico

                for log in mensajes:
                    if log.tracking_value_ids:
                        for cambio in log.tracking_value_ids:
                            if cambio.new_value_char == 'Para aprobar':
                                fecha_envio_cp = log.date
                                usuario_envio_cp = log.author_id.name
                                break
                    if fecha_envio_cp:
                        break  # Salir del bucle principal también una vez encontrada la fecha

                # Si no encontró cambio, usamos fecha vacía o algún valor por defecto
                fecha_llegada = order.date_planned.strftime('%Y-%m-%d') if order.date_planned else ''
                fecha_envio_cp_str = fecha_envio_cp.strftime('%Y-%m-%d') if fecha_envio_cp else 'N/A'
                dias_restantes = (
                    (fecha_envio_cp.date() - fields.Date.today()).days
                    if fecha_envio_cp else ''
                )

                url = f"{base_url}/web#id={order.id}&model=purchase.order&view_type=form"

                table_rows += f"""
                    <tr>
                        <td>{order.name}</td>
                        <td>{order.partner_id.name}</td>
                        <td>{order.solicitante.name}</td>
                        <td>{order.company_id.name}</td>
                        <td>{order.create_date.strftime('%Y-%m-%d')}</td>
                        <td>{fecha_envio_cp_str}</td>
                        <td>{usuario_envio_cp}</td>
                        <td>{dias_restantes}</td>
                        <td><a href="{url}">Aprobar</a></td>
                    </tr>
                """

            body_html = f"""
                <p>Estimado/a {user.name},</p>
                <p>Tiene las siguientes órdenes de compra pendientes por aprobar:</p>
                <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; font-family: Arial;">
                    <thead>
                        <tr style="background-color: #f2f2f2;">
                            <th>Orden</th>
                            <th>Proveedor</th>
                            <th>Solicitante</th>
                            <th>Compañía</th>
                            <th>Fecha Creación</th>
                            <th>F. Enviada a Aprobar</th>
                            <th>Usuario envio a Aprobar</th>
                            <th>Días Restantes</th>
                            <th>Acción</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
                <p>Por favor ingrese a Odoo para revisar y aprobar.</p>
            """

            # Enviar el correo
            self.env['mail.mail'].create({
                'subject': 'Órdenes de compra pendientes de aprobar por Financiero',
                'body_html': body_html,
                'email_to': user.email,
                'auto_delete': True,
            }).send()

    def send_pending_approval_emails_jcasal(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        aprobadores = self.env['res.users'].search([('id', '=', 31)])

        for user in aprobadores:
            # Filtrar órdenes asignadas a ese aprobador
            orders = self.env['purchase.order'].search([
                ('state', '=', 'to approve'),
                ('usuario_aprobacion_id','=',user.id)
            ])
            if not orders:
                continue

            table_rows = ""
            for order in orders:
                order = self.env['purchase.order'].browse(order.id)
                fecha_envio_cp = None  # Aquí se guardará la fecha del cambio a Control Presupuesto
                usuario_envio_cp = None
                mensajes = self.env['mail.message'].search([
                    ('model', '=', 'purchase.order'),
                    ('res_id', '=', order.id),
                    ('message_type', '=', 'notification')
                ], order='date asc')  # Aseguramos orden cronológico

                for log in mensajes:
                    if log.tracking_value_ids:
                        for cambio in log.tracking_value_ids:
                            if cambio.new_value_char == 'Para aprobar':
                                fecha_envio_cp = log.date
                                usuario_envio_cp = log.author_id.name
                                break
                    if fecha_envio_cp:
                        break  # Salir del bucle principal también una vez encontrada la fecha

                # Si no encontró cambio, usamos fecha vacía o algún valor por defecto
                fecha_llegada = order.date_planned.strftime('%Y-%m-%d') if order.date_planned else ''
                fecha_envio_cp_str = fecha_envio_cp.strftime('%Y-%m-%d') if fecha_envio_cp else 'N/A'
                dias_restantes = (
                    (fecha_envio_cp.date() - fields.Date.today()).days
                    if fecha_envio_cp else ''
                )

                url = f"{base_url}/web#id={order.id}&model=purchase.order&view_type=form"

                table_rows += f"""
                    <tr>
                        <td>{order.name}</td>
                        <td>{order.partner_id.name}</td>
                        <td>{order.solicitante.name}</td>
                        <td>{order.company_id.name}</td>
                        <td>{order.create_date.strftime('%Y-%m-%d')}</td>
                        <td>{fecha_envio_cp_str}</td>
                        <td>{usuario_envio_cp}</td>
                        <td>{dias_restantes}</td>
                        <td><a href="{url}">Aprobar</a></td>
                    </tr>
                """

            body_html = f"""
                <p>Estimado/a {user.name},</p>
                <p>Tiene las siguientes órdenes de compra pendientes por aprobar:</p>
                <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; font-family: Arial;">
                    <thead>
                        <tr style="background-color: #f2f2f2;">
                            <th>Orden</th>
                            <th>Proveedor</th>
                            <th>Solicitante</th>
                            <th>Compañía</th>
                            <th>Fecha Creación</th>
                            <th>F. Enviada a Aprobar</th>
                            <th>Usuario envio a Aprobar</th>
                            <th>Días Restantes</th>
                            <th>Acción</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
                <p>Por favor ingrese a Odoo para revisar y aprobar.</p>
            """

            # Enviar el correo
            self.env['mail.mail'].create({
                'subject': 'Órdenes de compra pendientes de aprobar',
                'body_html': body_html,
                'email_to': 'jcasal@gpsgroup.com.ec, amikly@gpsgroup.com.ec',#user.email,
                'auto_delete': True,
            }).send()

    def send_pending_approval_emails_jleon(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        aprobadores = self.env['res.users'].search([('id', '=', 40)])

        for user in aprobadores:
            # Filtrar órdenes asignadas a ese aprobador
            orders = self.env['purchase.order'].search([
                ('state', '=', 'to approve'),
                ('usuario_aprobacion_id','=',user.id)
            ])
            if not orders:
                continue

            table_rows = ""
            for order in orders:
                order = self.env['purchase.order'].browse(order.id)
                fecha_envio_cp = None  # Aquí se guardará la fecha del cambio a Control Presupuesto
                usuario_envio_cp = None
                mensajes = self.env['mail.message'].search([
                    ('model', '=', 'purchase.order'),
                    ('res_id', '=', order.id),
                    ('message_type', '=', 'notification')
                ], order='date asc')  # Aseguramos orden cronológico

                for log in mensajes:
                    if log.tracking_value_ids:
                        for cambio in log.tracking_value_ids:
                            if cambio.new_value_char == 'Para aprobar':
                                fecha_envio_cp = log.date
                                usuario_envio_cp = log.author_id.name
                                break
                    if fecha_envio_cp:
                        break  # Salir del bucle principal también una vez encontrada la fecha

                # Si no encontró cambio, usamos fecha vacía o algún valor por defecto
                fecha_llegada = order.date_planned.strftime('%Y-%m-%d') if order.date_planned else ''
                fecha_envio_cp_str = fecha_envio_cp.strftime('%Y-%m-%d') if fecha_envio_cp else 'N/A'
                dias_restantes = (
                    (fecha_envio_cp.date() - fields.Date.today()).days
                    if fecha_envio_cp else ''
                )

                url = f"{base_url}/web#id={order.id}&model=purchase.order&view_type=form"

                table_rows += f"""
                    <tr>
                        <td>{order.name}</td>
                        <td>{order.partner_id.name}</td>
                        <td>{order.solicitante.name}</td>
                        <td>{order.company_id.name}</td>
                        <td>{order.create_date.strftime('%Y-%m-%d')}</td>
                        <td>{fecha_envio_cp_str}</td>
                        <td>{usuario_envio_cp}</td>
                        <td>{dias_restantes}</td>
                        <td><a href="{url}">Aprobar</a></td>
                    </tr>
                """

            body_html = f"""
                <p>Estimado/a {user.name},</p>
                <p>Tiene las siguientes órdenes de compra pendientes por aprobar:</p>
                <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; font-family: Arial;">
                    <thead>
                        <tr style="background-color: #f2f2f2;">
                            <th>Orden</th>
                            <th>Proveedor</th>
                            <th>Solicitante</th>
                            <th>Compañía</th>
                            <th>Fecha Creación</th>
                            <th>F. Enviada a Aprobar</th>
                            <th>Usuario envio a Aprobar</th>
                            <th>Días Restantes</th>
                            <th>Acción</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
                <p>Por favor ingrese a Odoo para revisar y aprobar.</p>
            """

            # Enviar el correo
            self.env['mail.mail'].create({
                'subject': 'Órdenes de compra pendientes de aprobar',
                'body_html': body_html,
                'email_to': 'jleon@gpsgroup.com.ec, amikly@gpsgroup.com.ec',#user.email,
                'auto_delete': True,
            }).send()

    def _find_user_by_handle(self, handle):
        """Busca un usuario por login o email que contenga el handle (case-insensitive)."""
        # intenta login, email (res.users), y el correo del partner relacionado
        domain = ['|', '|',
                  ('login', 'ilike', handle),
                  ('email', 'ilike', handle),
                  ('partner_id.email', 'ilike', handle)]
        user = self.env['res.users'].sudo().search(domain, limit=1)
        return user

    def send_notifications_presidencia_adm(self):
        """
        Envía correos:
          - Si tipo_orden == 'presidencia' -> a 'aaviles'
          - Si tipo_orden == 'administrativa' -> a 'jhidalgo'
          - Si amount_untaxed > 5000 en cualquiera de los dos tipos -> también a 'szambrano'
        Solo considera órdenes en estado 'to approve'.
        """
        TYPE_FIELD = 'tipo_orden'          # cámbialo si tu campo se llama distinto
        TYPES_WATCHED = ('es_presidencia', 'es_admin')
        THRESHOLD = 5000.0                 # sin impuestos
        STATE_TO_WATCH = 'to approve'      # estado objetivo

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''

        # Mapea tipo -> handle primario
        primary_handles = {
            'es_presidencia': 'aaviles',
            'es_admin': 'jhidalgo',
        }
        threshold_handle = 'szambrano'  # adicional cuando > 5K sin impuestos

        # Resuelve usuarios (si no existen, simplemente no enviará a ese destino)
        primary_users = {}
        # for t, handle in primary_handles.items():
        #     primary_users[t] = self._find_user_by_handle(handle)

        # threshold_user = self._find_user_by_handle(threshold_handle)

        # Busca órdenes a notificar
        domain = [
           ('state', '=', STATE_TO_WATCH),
            '|', ('es_admin', '=', True), ('es_presidencia', '=', True),
        ]
        orders = self.env['purchase.order'].sudo().search(domain)
        if not orders:
            return  # nada que enviar

        # Agrupa por destinatario (user.id) las órdenes que le corresponden
        # Enviamos un correo por destinatario con su tabla de órdenes
        orders_by_user = defaultdict(list)

        for po in orders:
            po_type = getattr(po, TYPE_FIELD, False)
            if po_type in primary_users and primary_users[po_type]:
                orders_by_user[primary_users[po_type].id].append(po)

            # Si supera el umbral, también para threshold_user (si existe)
            if po.amount_untaxed and po.amount_untaxed > THRESHOLD and threshold_user:
                orders_by_user[threshold_user.id].append(po)

        Mail = self.env['mail.mail'].sudo()

        # Construye y envía correos por usuario
        for user_id, po_list in orders_by_user.items():
            user = self.env['res.users'].browse(user_id)
            if not user or not user.partner_id.email:
                # Si no tiene email definido, omite
                continue

            table_rows = self._build_rows_html(po_list, base_url)
            body_html = f"""
                <p>Estimad@ {user.name},</p>
                <p>Estas son las órdenes de compra pendientes por aprobar asociadas a su rol:</p>
                <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; font-family: Arial; font-size: 13px;">
                    <thead>
                        <tr style="background-color:#f2f2f2;">
                            <th>Orden</th>
                            <th>Proveedor</th>
                            <th>Solicitante</th>
                            <th>Compañía</th>
                            <th>Fecha Creación</th>
                            <th>Fecha Planificada</th>
                            <th>Subtotal (s/ imp.)</th>
                            <th>Tipo</th>
                            <th>Acción</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
                <p>Por favor revise y proceda con la aprobación en Odoo.</p>
            """

            Mail.create({
                'subject': 'Órdenes de compra pendientes por aprobar',
                'body_html': body_html,
                'email_to': user.partner_id.email,  # correo del destinatario
                'auto_delete': True,
            }).send()

    def send_pending_approval_emails_mmorquecho(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        aprobadores = self.env['res.users'].search([('id', '=', 30)])

        for user in aprobadores:
            # Filtrar órdenes asignadas a ese aprobador
            orders = self.env['purchase.order'].search([
                ('state', '=', 'control_presupuesto'),
                #('id','in',[482])
            ])
            if not orders:
                continue

            table_rows = ""
            for order in orders:
                order = self.env['purchase.order'].browse(order.id)
                fecha_envio_cp = None  # Aquí se guardará la fecha del cambio a Control Presupuesto
                usuario_envio_cp = None
                mensajes = self.env['mail.message'].search([
                    ('model', '=', 'purchase.order'),
                    ('res_id', '=', order.id),
                    ('message_type', '=', 'notification')
                ], order='date asc')  # Aseguramos orden cronológico

                for log in mensajes:
                    if log.tracking_value_ids:
                        for cambio in log.tracking_value_ids:
                            if cambio.new_value_char == 'Control Presupuesto':
                                fecha_envio_cp = log.date
                                usuario_envio_cp = log.author_id.name
                                break
                    if fecha_envio_cp:
                        break  # Salir del bucle principal también una vez encontrada la fecha

                # Si no encontró cambio, usamos fecha vacía o algún valor por defecto
                fecha_llegada = order.date_planned.strftime('%Y-%m-%d') if order.date_planned else ''
                fecha_envio_cp_str = fecha_envio_cp.strftime('%Y-%m-%d') if fecha_envio_cp else 'N/A'
                dias_restantes = (
                    (fecha_envio_cp.date() - fields.Date.today()).days
                    if fecha_envio_cp else ''
                )

                url = f"{base_url}/web#id={order.id}&model=purchase.order&view_type=form"

                table_rows += f"""
                    <tr>
                        <td>{order.name}</td>
                        <td>{order.partner_id.name}</td>
                        <td>{order.solicitante.name}</td>
                        <td>{order.company_id.name}</td>
                        <td>{order.create_date.strftime('%Y-%m-%d')}</td>
                        <td>{fecha_envio_cp_str}</td>
                        <td>{usuario_envio_cp}</td>
                        <td>{dias_restantes}</td>
                        <td><a href="{url}">Aprobar</a></td>
                    </tr>
                """

            body_html = f"""
                <p>Estimado/a {user.name},</p>
                <p>Tiene las siguientes órdenes de compra pendientes por aprobar en control de presupuesto:</p>
                <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; font-family: Arial;">
                    <thead>
                        <tr style="background-color: #f2f2f2;">
                            <th>Orden</th>
                            <th>Proveedor</th>
                            <th>Solicitante</th>
                            <th>Compañía</th>
                            <th>Fecha Creación</th>
                            <th>F. Enviada a Ctrl. Presup</th>
                            <th>Usuario envio a Ctrl. Presup</th>
                            <th>Días Restantes</th>
                            <th>Acción</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
                <p>Por favor ingrese a Odoo para revisar y aprobar.</p>
            """

            # Enviar el correo
            self.env['mail.mail'].create({
                'subject': 'Órdenes de compra en control presupuestario',
                'body_html': body_html,
                'email_to': 'amikly@gpsgroup.com.ec, mmorquecho@gpsgroup.com.ec, dpincay@gpsgroup.com.ec, hponce@gpsgroup.com.ec, iposligua@gpsgroup.com.ec',#user.email,
                'auto_delete': True,
            }).send()

    def generate_excel_and_send_email(self):
        # Crear un archivo Excel en memoria
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Reporte')
        currency_format = workbook.add_format({'num_format': '$#,##0.00'})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        # Escribir algunos datos de ejemplo
        worksheet.write('A1', 'Fecha Creacion')
        worksheet.write('B1', 'Fecha Confirmacion')
        worksheet.write('C1', 'Company')
        worksheet.write('D1', 'Cuenta Analitica')
        worksheet.write('E1', 'Origen')
        worksheet.write('F1', 'Solicitante')
        worksheet.write('G1', 'Comprador')
        worksheet.write('H1', 'Referencia del Pedido')
        worksheet.write('I1', 'Proveedor')
        worksheet.write('J1', 'Estado')
        worksheet.write('K1', 'Aprobacion Financiero')
        worksheet.write('L1', 'Estado Facturacion')
        worksheet.write('M1', 'Producto')
        worksheet.write('N1', 'Rubro')
        worksheet.write('O1', 'Descripcion')
        worksheet.write('P1', 'Tipo Orden')
        worksheet.write('Q1', 'Precio Unitario')
        worksheet.write('R1', 'Precio Venta')
        worksheet.write('S1', 'Descuento')
        worksheet.write('T1', 'Cantidad')
        worksheet.write('U1', 'Subtotal PSP')
        worksheet.write('V1', 'Base Imponible')
        worksheet.write('W1', 'Base Imponible Total')
        companies = self.env['res.company'].search([])
        row = 1
        self = self.with_context(active_test=False)
        for company in companies:
            orders = self.env['purchase.order'].sudo().search([('company_id', '=', company.id)])
            tipo_orden = ''
            status_fact = ''
            for record in orders:  # Ejemplo: obtendremos los 10 primeros contactos
                #try:
                for det in record.order_line:
                    if det.analytic_distribution:
                        first_key = next(iter(det.analytic_distribution))
                        #centro_costo = self.env['account.analytic.account'].browse(int(first_key)).name
                        centro_costo = self.env['account.analytic.account'].browse(int(first_key)).exists()
                        centro_costo = centro_costo.name if centro_costo else 'No Asignado'
                    else:
                        centro_costo = 'No Asignado'
                    if str(record.purchase_order_type) == 'service':
                        tipo_orden = 'Servicio'
                    elif str(record.purchase_order_type) == 'product':
                        tipo_orden = 'Producto'
                    else:
                        tipo_orden = 'Producto y Servicio'
                    if str(record.invoice_status) == 'no':
                        status_fact = 'Nada a Facturar'
                    elif str(record.invoice_status) == 'to invoice':
                        status_fact = 'Facturas en espera'
                    else:
                        status_fact = 'Totalmente Facturado'
                    if str(record.state)=='draft':
                        estado = 'SdP'
                    elif str(record.state)=='sent':
                        estado = 'Enviado'
                    elif str(record.state)=='purchase':
                        estado = 'Orden de Compra'
                    elif str(record.state)=='done':
                        estado = 'Realizado'
                    elif str(record.state)=='cancel':  
                        estado = 'Cancelado'
                    else:
                        estado = 'Por Aprobar'

                    worksheet.write(row, 0, record.create_date, date_format)
                    worksheet.write(row, 1, record.date_approve, date_format)
                    worksheet.write(row, 2, record.company_id.name)
                    worksheet.write(row, 3, str(centro_costo))
                    worksheet.write(row, 4, record.origin)
                    worksheet.write(row, 5, str(record.solicitante.name))
                    worksheet.write(row, 6, str(record.user_id.name))
                    worksheet.write(row, 7, str(record.name))
                    worksheet.write(row, 8, str(record.partner_id.name))
                    worksheet.write(row, 9, str(estado))
                    worksheet.write(row, 10, 'Si' if record.requiere_aprobacion else 'No')
                    worksheet.write(row, 11, str(status_fact))
                    worksheet.write(row, 12, str(det.product_id.name))
                    worksheet.write(row, 13, str(det.rubro))
                    worksheet.write(row, 14, str(det.name))
                    worksheet.write(row, 15, str(tipo_orden))
                    worksheet.write(row, 16, det.price_unit, currency_format)
                    worksheet.write(row, 17, det.precio_venta, currency_format)
                    worksheet.write(row, 18, str(det.discount))
                    worksheet.write(row, 19, str(det.product_qty))
                    worksheet.write(row, 20, (det.product_qty * det.precio_venta), currency_format)
                    worksheet.write(row, 21, det.price_subtotal, currency_format)
                    worksheet.write(row, 22, record.amount_untaxed, currency_format)
                    row += 1

        workbook.close()
        output.seek(0)
        excel_data = output.read()
        output.close()

        # Codificar el archivo en base64
        excel_base64 = base64.b64encode(excel_data)

        # Crear un adjunto para el correo
        attachment = self.env['ir.attachment'].create({
            'name': 'ReporteOC.xlsx',
            'type': 'binary',
            'datas': excel_base64,
            'store_fname': 'Reporte.xlsx',
            'res_model': 'excel.report.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        # Enviar el correo
        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)
        
        # Obtener la fecha y hora actual en UTC y convertirla a la zona horaria local
        current_datetime = fields.Datetime.now()
        current_datetime_local = pytz.utc.localize(current_datetime).astimezone(local_tz)
        mail_values = {
            'subject': f'ACTUALIZACIÓN DATOS OC ODOO {current_datetime_local}',
            'body_html': '<p>Adjunto encontrarás el reporte de OC en formato Excel.</p>',
            'email_to': 'mmorquecho@gpsgroup.com.ec',
            #'email_to': 'wguijarro@gpsgroup.com.ec',
            'attachment_ids': [(6, 0, [attachment.id])],
        }
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Correo Enviado',
                'message': 'El reporte en Excel ha sido enviado correctamente.',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def generate_excel_and_send_email_aprobadas(self):
        # Crear un archivo Excel en memoria
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Reporte')
        currency_format = workbook.add_format({'num_format': '$#,##0.00'})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        sql_mo = """
            SELECT rc.name compania, 
            po.name orden, 
            rp2.name comprador,
            (po.date_approve - interval '5 hours')::date AS fecha_app, 
              rp.name AS proveedor, 
              po.amount_total total
            FROM purchase_order po
            JOIN res_partner rp ON po.partner_id = rp.id
                JOIN res_company rc on po.company_id = rc.id
				JOIN res_users ru ON ru.id = po.user_id
				JOIN res_partner rp2 ON rp2.id = ru.partner_id
            WHERE po.state = 'purchase'
            AND date_approve >= (CURRENT_DATE - INTERVAL '1 day')
			AND date_approve < (CURRENT_DATE)
            order by 1,2
        """
        self.env.cr.execute(sql_mo)
        # Escribir algunos datos de ejemplo
        worksheet.write('A1', 'Company')
        worksheet.write('B1', 'Orden de Compra')
        worksheet.write('C1', 'Comprador')
        worksheet.write('D1', 'Fecha')
        worksheet.write('E1', 'Proveedor')
        worksheet.write('F1', 'Total')
        
        row = 1
        # Lee y recorre los resultados
        results = self.env.cr.fetchall()
        for x in results:
            # Aquí puedes acceder a cada columna de la fila, por ejemplo:
            worksheet.write(row, 0, x[0])
            worksheet.write(row, 1, x[1])
            worksheet.write(row, 2, x[2])
            worksheet.write(row, 3, x[3], date_format)
            worksheet.write(row, 4, x[4])
            worksheet.write(row, 5, x[5], currency_format)
            
            row += 1

        workbook.close()
        output.seek(0)
        excel_data = output.read()
        output.close()

        # Codificar el archivo en base64
        excel_base64 = base64.b64encode(excel_data)

        # Crear un adjunto para el correo
        attachment = self.env['ir.attachment'].create({
            'name': 'OrdenCompraAprobas.xlsx',
            'type': 'binary',
            'datas': excel_base64,
            'store_fname': 'OrdenCompraAprobas.xlsx',
            'res_model': 'excel.report.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        # Enviar el correo
        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)
        
        # Obtener la fecha y hora actual en UTC y convertirla a la zona horaria local
        current_datetime = fields.Datetime.now()
        current_datetime_local = pytz.utc.localize(current_datetime).astimezone(local_tz)
        mail_values = {
            'subject': f'Ordenes de Compras Aprobadas {current_datetime_local}',
            'body_html': '<p>Adjunto encontrarás el detalle de OC Aprobadas en formato Excel.</p>',
            'email_to': 'colmedo@gpsgroup.com.ec, jleon@gpsgroup.com.ec, mvivas@gpsgroup.com.ec, gorellana@gpsgroup.com.ec, giturralde@gpsgroup.com.ec, avelez@gpsgroup.com.ec, abenavides@gpsgroup.com.ec, wguijarro@gpsgroup.com.ec, aimbaquingo@gpsgroup.com.ec',#,mmorquecho
            'attachment_ids': [(6, 0, [attachment.id])],
        }
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Correo Enviado',
                'message': 'El reporte en Excel ha sido enviado correctamente.',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def button_descargar(self):
        for record in self:
            # Crear el archivo Excel en memoria
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output)
            sheet = workbook.add_worksheet('OrdenCompra')

            # Formatos
            title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
            header_format = workbook.add_format({'bold': True, 'align': 'left'})
            value_format = workbook.add_format({'align': 'left'})

            # Cabecera principal
            sheet.write('A1', record.company_id.name, title_format)
            sheet.write('G1', 'ORDEN DE COMPRA', title_format)

            # Detalles de la cabecera
            sheet.write('A2', 'OC:', header_format)

            sheet.write('A3', 'PROVEEDOR:', header_format)

            
            # Espaciado para la tabla
            row = 2
            # Encabezados de la tabla
            headers = ['#ID','Producto','Descripcion', 'Rubro', 'TipoCosto','CtaAnalitica','Unidad', 'Cantidad', 'Precio Unitario', 'Precio Venta']
            for col, header in enumerate(headers):
                sheet.write(row, col, header, header_format)
            row = row + 1
            sum = 0
            for line in record.order_line:
                sheet.write(row, 0, line.id)
                sheet.write(row, 1, line.product_id.default_code or '')
                sheet.write(row, 2, line.name or '')
                sheet.write(row, 3, line.rubro or '')
                sheet.write(row, 4, line.tipo_costo_id.name or '')
                sheet.write(row, 5, json.dumps(line.analytic_distribution))
                sheet.write(row, 6, line.product_id.uom_po_id.name or '')
                sheet.write(row, 7, line.product_qty)
                sheet.write(row, 8, line.price_unit)
                if self.env.user.has_group('account_payment_purchase.group_analytic_user'):
                    sheet.write(row, 9, line.precio_venta)
                else:
                    sheet.write(row, 9, 0)
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
    
class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    
    rubro = fields.Char(string='Rubro')
    descuento_presupuesto = fields.Float('Dscto. Psto')
    precio_venta = fields.Float('Precio de Venta')
    is_editable_custom = fields.Boolean(
        compute="_compute_editable_fields",
        string="Custom Field Editable",
        store=True
    )
    is_editable_reception = fields.Boolean(
        compute="_compute_editable_fields",
        string="Reception Field Editable",
        store=True
    )
    tipo_costo = fields.Selection([
        ('ManoObra', 'Mano de obra'),
        ('Material', 'Material'),
        ('Equipo', 'Equipo'),
        ('Transporte', 'Transporte'),
        ('Indirecto', 'Indirecto'),
        ('Administrativo', 'Administrativo'),
        ('Garantia', 'Garantia'),
        ], 'Tipo Costo', default='Material')
    tipo_costo_id = fields.Many2one('tipo.costo','Tipo Costo')
    analytic_account_names = fields.Char(
        string='Cuentas Analíticas',
        compute='_compute_analytic_account_names',
        store = True
    )
    margen = fields.Float('Margen Bruto', compute='_compute_margen_bruto', store = True)
    precio_real = fields.Float('Precio Real', compute='_compute_precio_real', store = True)
    margen_con_dscto = fields.Float('M. Bruto con Dscto.', compute='_compute_margen_bruto_con_dscto', store = True)
    subtotal_precio_real = fields.Float('SubTot P.Real', compute='_compute_subtotal_precio_real', store = True)
    subtotal_precio_sin_dscto = fields.Float('SubTot P.Sin Dscto', compute='_compute_subtotal_precio_sin_dscto', store = True)

    @api.constrains('taxes_id')
    def _check_taxes_for_import(self):
        for line in self:
            if line.order_id.importacion and line.taxes_id:
                raise UserError(_("No se deben asignar impuestos en órdenes de compra de tipo 'Importación'."))
            
    @api.depends('precio_venta', 'product_qty')
    def _compute_subtotal_precio_sin_dscto(self):
        for record in self:
            record.subtotal_precio_sin_dscto = record.precio_venta * record.product_qty

    @api.depends('precio_real', 'product_qty')
    def _compute_subtotal_precio_real(self):
        for record in self:
            record.subtotal_precio_real = record.precio_real * record.product_qty

    @api.depends('precio_real', 'discount', 'price_unit')
    def _compute_margen_bruto_con_dscto(self):
        for record in self:
            precio_unit = record.price_unit or 0.0
            discount = record.discount or 0.0
            precio_con_descuento = precio_unit * (1 - discount / 100)

            if record.precio_real > 0:
                record.margen_con_dscto = 1 - (precio_con_descuento / record.precio_real)
            else:
                record.margen_con_dscto = 0.0

    @api.depends('precio_venta','descuento_presupuesto')
    def _compute_precio_real(self):
        for x in self:
            precio_unit = 0
            if x.precio_venta and x.descuento_presupuesto:  # evita división por cero
                x.precio_real = x.precio_venta * (1-x.descuento_presupuesto)
            else:
                x.precio_real = 0.0  # o puedes poner False o None si prefieres

    @api.depends('precio_venta', 'price_unit', 'discount')
    def _compute_margen_bruto(self):
        for record in self:
            precio_unit = record.price_unit or 0.0
            precio_venta = record.precio_venta or 0.0
            discount = record.discount or 0.0

            if precio_venta > 0 and precio_unit > 0:
                precio_con_descuento = precio_unit * (1 - discount / 100)
                record.margen = 1 - (precio_con_descuento / precio_venta)
            else:
                record.margen = 0.0


    @api.depends('analytic_distribution')
    def _compute_analytic_account_names(self):
        for line in self:
            if isinstance(line.analytic_distribution, dict):
                # Obtiene los IDs de las cuentas analíticas
                analytic_account_ids = list(line.analytic_distribution.keys())
                # Busca los nombres de las cuentas analíticas utilizando esos IDs
                analytic_accounts = self.env['account.analytic.account'].search([('id', 'in', analytic_account_ids)])
                line.analytic_account_names = ', '.join(analytic_accounts.mapped('name'))
            else:
                line.analytic_account_names = ''

    @api.depends('product_id.type', 'order_id.state')
    def _compute_editable_fields(self):
        for line in self:
            # line.is_editable_custom = line.state not in [
            #     'control_presupuesto', 'to approve', 'purchase', 'done', 'cancel'
            # ]
            if line.order_id.state in ['control_presupuesto', 'to approve', 'purchase', 'done', 'cancel']:  # Adjust state as needed
                if line.product_id.detailed_type == 'product':
                    line.is_editable_custom = True
                    line.is_editable_reception = False
                elif line.product_id.detailed_type == 'service':
                    line.is_editable_custom = True
                    line.is_editable_reception = True
                else:
                    line.is_editable_custom = False
                    line.is_editable_reception = False
            else:
                line.is_editable_custom = False
                line.is_editable_reception = False

    @api.constrains('analytic_distribution')
    def _check_analytic_distribution(self):
        for record in self:
            if not record.analytic_distribution and not record.custom_requisition_line_id and record.display_type!='line_section': 
                raise UserError(_("No puedes crear o modificar una orden de compra sin haber ingresado la distribución analítica."))
            
    @api.model
    def default_get(self, fields_list):
        defaults = super(PurchaseOrderLine, self).default_get(fields_list)
        tipo_costo = self.env['tipo.costo'].search([('code', '=', 'MT')], limit=1)
        if tipo_costo:
            defaults['tipo_costo_id'] = tipo_costo.id
        return defaults

    # @api.model
    # def write(self, vals):
    #     for line in self:
    #         if line.order_id.state == 'purchase' and 'price_unit' in vals:
    #             new_price = vals['price_unit']
    #             if new_price > line.price_unit:
    #                 raise UserError(_("No se puede aumentar el precio unitario en una orden ya confirmada. Solo se permiten reducciones."))
    #             if line.qty_received > 0:
    #                 raise UserError(_(
    #                     "No se puede modificar el precio unitario porque ya se ha recibido mercancía para esta línea."
    #                 ))
    #     return super(PurchaseOrderLine, self).write(vals)