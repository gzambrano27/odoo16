from odoo import models, fields, api, _
from odoo.exceptions import UserError,ValidationError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    state = fields.Selection(selection_add=[
        ('control_presupuesto', 'Control Presupuesto')
    ], ondelete={'control_presupuesto': 'set draft'})

    mostrar_excepcion_confirmacion=fields.Boolean(string="Mostrar Excepciión Compra",compute="_get_compute_mostrar_excepcion_confirmacion",store=False)
    excepcion_confirmacion=fields.Boolean("Excepción Compra",default=False,tracking=True)
    excepcion_confirmacion_comments = fields.Text("Comentario Excepción Compra", default=False,tracking=True)
    is_editable = fields.Boolean(compute='_compute_is_editable', store=False)

    @api.depends('state')
    def _compute_is_editable(self):
        for record in self:
            record.is_editable = record.state not in [
                'control_presupuesto', 'to approve', 'purchase', 'done', 'cancel'
            ]

    
    #comentado
    #@api.onchange('order_line')
    #@api.depends('order_line')
    def _get_compute_mostrar_excepcion_confirmacion(self):
        for brw_each  in self:
            x = []# comentado brw_each.order_line.filtered(lambda x: x.margen_last_purchase_move_line_decoration == 'danger')
            mostrar_excepcion_confirmacion=(x and len(x)>0)
            brw_each.mostrar_excepcion_confirmacion=mostrar_excepcion_confirmacion

    def validar_margenes(self):
        v=True#super(PurchaseOrder,self).validar_margenes()
        return v

    def button_control_presupuesto(self):
        """Set the state to 'control_presupuesto'."""
        for order in self:
            order.validate_state_advance_payment()
            order.state = 'control_presupuesto'

    def button_confirm(self):
        """
        Override the confirm button to add an intermediate step 'control_presupuesto'.
        """
        for order in self:
            if order.es_admin:
                if not self.env.user.has_group('account_payment_purchase.group_purchase_user_administrativo'):
                    raise UserError(_("No tienes permiso para confirmar la solicitud de compra administrativo!!."))
            if self.env.user.has_group('account_payment_purchase.group_purchase_user_registrador') and order.amount_untaxed!=0:
                raise UserError(_("No tienes permiso para confirmar la solicitud de compra!!."))
            if order.state == 'draft' or order.state == 'sent':  # Si está en borrador, pasa a control_presupuesto
                order.validate_state_advance_payment()
                if not order.es_admin:
                    order.state = 'control_presupuesto'
                if self.amount_total==0 or order.es_admin:
                    if not order.es_admin:
                        order.button_approve() 
                    else:
                        order.write({'state': 'to approve'})     
            elif order.state == 'control_presupuesto':  # Si ya está en control_presupuesto, sigue al flujo normal
                order._check_analytic_account_1()
                order._check_analytic_distribution()
                order.validar_margenes()
                if not self.env.user.has_group('account_payment_purchase.group_purchase_user_presupuesto'):
                    raise UserError(_("No tienes permiso para enviar a aprobar la solicitud de compra!!."))
                if order.state not in ['draft', 'sent','control_presupuesto']:
                    continue
                order.validate_state_advance_payment()
                order.order_line._validate_analytic_distribution()
                order._add_supplier_to_product()
                # Deal with double validation process
                if order._approval_allowed():
                    #Logica para hacer la aprobacion de ordenes de compra
                    usuario_aprobacion_id, requiere_aprobacion = self._get_usuario_aprobacion(self.amount_untaxed,self.es_admin)#self.amount_total)
                    if requiere_aprobacion:
                        if self.requiere_aprobacion:
                            raise UserError(_("No puedes registrar una orden de compra que no ha sido verificada por Financiero!!!"))
                    usuario_aprobacion = self.env.user.id
                    requiere_aprobacion = False
                    settings = self.env['config.settings.approval.po'].search([('estado','=','activo')])
                    for x in settings:
                        print (x.monto_desde)
                        #if x.monto_desde <= self.amount_total <= x.monto_hasta:
                        if x.monto_desde <= self.amount_untaxed <= x.monto_hasta and x.usuario_id.id==self.env.user.id:
                            usuario_aprobacion = x.usuario_id.id
                            #if usuario_aprobacion!=self.env.user.id and self.amount_total > x.monto_hasta:
                            if usuario_aprobacion!=self.env.user.id and self.amount_untaxed > x.monto_hasta:
                                #voy a buscar si el usuario diferente esta en la tabla de configuraciones
                                if not self.env['config.settings.approval.po'].search([('estado', '=', 'activo'),('usuario_id','=',self.env.user.id),('monto_desde','>=',self.amount_total)]):
                                    raise UserError(_("No puedes registrar una orden de compra que supera tu maximo de aprobacion, max permitido %s!!!")%(str(float(x.monto_hasta))))
                    order.button_approve()
                else:
                    order.write({'state': 'to approve'})
                if order.partner_id not in order.message_partner_ids:
                    order.message_subscribe([order.partner_id.id])
            return True
                #super(PurchaseOrder, order).button_confirm()

    # Sobreescribe la lista de selección para establecer el orden deseado
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(PurchaseOrder, self).fields_get(allfields, attributes)
        if 'state' in res and 'selection' in res['state']:
            # Reorganizar los estados en el orden deseado
            res['state']['selection'] = [
                ('draft', 'SdP'),
                ('control_presupuesto', 'Control Presupuesto'),
                ('sent', 'SDP Enviada'),
                ('to approve', 'Para aprobar'),
                ('purchase', 'Orden de compra'),
                ('done', 'Bloqueada'),
                ('cancel', 'Cancelado'),
            ]
        return res