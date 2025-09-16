from odoo import models, fields, api, _
from odoo.exceptions import UserError,ValidationError

FINANCE_GROUP = 'account_payment_purchase.group_account_financiero_app'
PRESUP_GROUP = 'account_payment_purchase.group_purchase_user_presupuesto'
ADMIN_GROUP = 'account_payment_purchase.group_purchase_user_administrativo'
REG_GROUP = 'account_payment_purchase.group_purchase_user_registrador'


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    FINANCE_THRESHOLD = 20000.0  # 20K sin impuestos

    state = fields.Selection(selection_add=[
        ('control_presupuesto', 'Control Presupuesto'),
        ('financiero', 'Financiero')
    ], ondelete={'control_presupuesto': 'set draft'})

    mostrar_excepcion_confirmacion=fields.Boolean(string="Mostrar Excepciión Compra",compute="_get_compute_mostrar_excepcion_confirmacion",store=False)
    excepcion_confirmacion=fields.Boolean("Excepción Compra",default=False,tracking=True)
    excepcion_confirmacion_comments = fields.Text("Comentario Excepción Compra", default=False,tracking=True)
    is_editable = fields.Boolean(compute='_compute_is_editable', store=False)

    @api.depends('state')
    def _compute_is_editable(self):
        for record in self:
            record.is_editable = record.state not in [
                'control_presupuesto', 'financiero','to approve', 'purchase', 'done', 'cancel'
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

    def action_finance_review(self):
        """Revisión financiera: solo Finanzas puede pasar de 'financiero' a 'to approve'."""
        self.ensure_one()
        if not self.env.user.has_group(FINANCE_GROUP):
            raise UserError(_("No tienes permiso de Finanzas para aprobar la revisión financiera."))
        if self.state != 'financiero':
            raise UserError(_("La orden debe estar en estado 'Financiero' para esta acción."))
        # Aquí NO aprobamos la OC; solo dejamos lista para la aprobación normal
        self.state = 'to approve'
        return True
    
    def _get_std_po_approver(self, amount_untaxed):
        """Devuelve (approver_id, requiere_aprobacion) desde config.settings.approval.po por rango."""
        Setting = self.env['config.settings.approval.po'].sudo()
        domain = [
            ('monto_desde', '<=', amount_untaxed or 0.0),
            ('monto_hasta', '>=', amount_untaxed or 0.0),
        ]
        # filtros opcionales si existen en el modelo
        if 'company_id' in Setting._fields:
            # usa la compañía de la OC
            domain.append(('company_id', '=', self.company_id.id if len(self) == 1 else False))
        if 'estado' in Setting._fields:
            domain.append(('estado', '=', 'activo'))

        rec = Setting.search(domain, order='monto_desde asc', limit=1)
        if not rec:
            return False, False

        approver_id = rec.usuario_id.id if rec.usuario_id else False
        requiere = bool(getattr(rec, 'requiere_aprobacion', False))
        return approver_id, requiere

    def _get_admin_po_approver(self, amount_untaxed, solicitante_id=None):
        AdminSetting = self.env['config.settings.approval.po.admin'].sudo()
        rec = AdminSetting.search([
            ('monto_desde', '<=', amount_untaxed or 0.0),
            ('monto_hasta', '>=', amount_untaxed or 0.0),
        ], order='monto_desde asc', limit=1)
        if not rec:
            return False, False, False

        approver_id = rec.usuario_id.id if rec.usuario_id else False
        requiere_aprob = bool(getattr(rec, 'requiere_aprobacion', False))
        # usar el nombre técnico correcto (Many2one)
        creador_id = rec.usuario_creador.id if hasattr(rec, 'usuario_creador') and rec.usuario_creador else False
        return approver_id, requiere_aprob, creador_id

    def button_confirm1(self):
        for order in self:
            # --- permisos base ---
            if getattr(order, 'es_admin', False) and not self.env.user.has_group(ADMIN_GROUP):
                raise UserError(_("No tienes permiso para confirmar una OC administrativa."))
            if self.env.user.has_group(REG_GROUP) and order.amount_untaxed != 0:
                raise UserError(_("No tienes permiso para confirmar esta OC."))

            # --- si total = 0, aprueba directo ---
            if order.amount_total == 0:
                order.write({'state': 'purchase'})
                continue

            # --- flujo especial Admin/Presidencia ---
            if order._is_admin_o_presi():
                if order._try_set_admin_presi_approver():
                    return True
                continue

            # --- flujo normal (NO admin/presidencia) ---
            amount_base = order.amount_untaxed or 0.0
            approver_id, _req = order._get_std_po_approver(amount_base)
            if not approver_id:
                raise UserError(_("No existe aprobador configurado para el monto %s.") % amount_base)

            vals = {'usuario_aprobacion_id': approver_id}

            # Siempre primero a control_presupuesto
            vals['state'] = 'control_presupuesto'
            order.write(vals)

            # Decisión según monto
            if amount_base >= self.FINANCE_THRESHOLD:
                order.write({'state': 'financiero'})
                # ahora que ya pasó por financiero → to approve
                order.write({'state': 'to approve'})
                order._create_approval_activity(approver_id)
            else:
                # monto menor a umbral → directo a to approve
                order.write({'state': 'to approve'})
                order._create_approval_activity(approver_id)

        return True
    
    def _create_approval_activity(self, approver_id, es_admin=False):
        for order in self:
            if order.state == 'to approve' and approver_id:
                order.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=approver_id,
                    summary=_('Aprobar OC (Administrativa/Presidencia)') if es_admin else _('Aprobar OC'),
                    note=_('Orden %s requiere tu aprobación. Monto (base): %s') % (order.name, order.amount_untaxed),
                )

    def button_confirm(self):
        # --- permisos base ---
        for order in self:
            if getattr(order, 'es_admin', False) and not self.env.user.has_group(ADMIN_GROUP):
                raise UserError(_("No tienes permiso para confirmar la solicitud de compra administrativo!!."))

            if self.env.user.has_group(REG_GROUP) and order.amount_untaxed != 0:
                raise UserError(_("No tienes permiso para confirmar la solicitud de compra!!."))

        # --- flujo especial Admin/Presidencia (usa la tabla config.settings.approval.po.admin) ---
        # Si ya deja la OC en 'to approve' con usuario_aprobacion_id, cortamos aquí.
        if self.amount_total > 0:
            if self._try_set_admin_presi_approver():
                return True
        band_p = 0
        # --- flujo normal (NO admin/presidencia) ---
        for order in self:
            # 1) draft/sent -> control_presupuesto (igual a tu lógica previa)
            if order.state in ('draft', 'sent'):
                if hasattr(order, 'validate_state_advance_payment'):
                    order.validate_state_advance_payment()
                band_p = 0
                if not getattr(order, 'es_admin', False):
                    order.state = 'control_presupuesto'
                    band_p = 1

                # NUEVA LÓGICA
                if order.amount_total == 0:
                    # aprobar directo si el total es 0
                    order.button_approve()
                    continue

                if getattr(order, 'es_admin', False) and band_p==0:
                    order.write({'state': 'to approve'})
                    continue

            # 2) control_presupuesto -> financiero / to approve (lee config.settings.approval.po)
            if order.state == 'control_presupuesto':
                if not self.env.user.has_group(PRESUP_GROUP):
                    raise UserError(_("Solo el grupo de Presupuesto puede enviar una orden desde 'Control Presupuesto'."))
                # Validaciones si existen
                for fn in ('_check_analytic_account_1', '_check_analytic_distribution', 'validar_margenes'):
                    if hasattr(order, fn):
                        getattr(order, fn)()
                if hasattr(order, 'validate_state_advance_payment'):
                    order.validate_state_advance_payment()
                if hasattr(order.order_line, '_validate_analytic_distribution'):
                    order.order_line._validate_analytic_distribution()
                if hasattr(order, '_add_supplier_to_product'):
                    order._add_supplier_to_product()

                amount_base = order.amount_untaxed or 0.0

                # Buscar aprobador estándar por rango en config.settings.approval.po
                Setting = self.env['config.settings.approval.po'].sudo()
                domain = [
                    ('monto_desde', '<=', amount_base),
                    ('monto_hasta', '>=', amount_base),
                ]
                # filtros opcionales si existen
                if 'company_id' in Setting._fields:
                    domain.append(('company_id', '=', order.company_id.id))
                if 'estado' in Setting._fields:
                    domain.append(('estado', '=', 'activo'))

                rec = Setting.search(domain, order='monto_desde asc', limit=1)
                if not rec or not getattr(rec, 'usuario_id', False):
                    raise UserError(_("No existe un aprobador configurado en Parámetros Aprobación (config.settings.approval.po) para el monto %s.") % amount_base)

                approver_id = rec.usuario_id.id
                vals = {'usuario_aprobacion_id': approver_id}

                # Umbral financiero
                if amount_base >= self.FINANCE_THRESHOLD:
                    vals['state'] = 'financiero' if band_p == 0 else order.state
                    order.write(vals)
                else:
                    vals['state'] = 'to approve' if band_p == 0 else order.state
                    order.write(vals)
                    # tarea al aprobador
                    try:
                        if band_p == 0:
                            order.activity_schedule(
                                'mail.mail_activity_data_todo',
                                user_id=approver_id,
                                summary=_('Aprobar OC'),
                                note=_('Orden %s requiere tu aprobación. Monto (base): %s') % (order.name or '', amount_base),
                            )
                    except Exception:
                        pass

                # Suscribir proveedor
                if order.partner_id and order.partner_id not in order.message_partner_ids:
                    order.message_subscribe([order.partner_id.id])
                continue

        return True

    def _try_set_admin_presi_approver(self):
        """
        OC administrativa/presidencia:
        1) Buscar por rango + usuario_creador == solicitante
        2) Si no hay, buscar por rango + usuario_creador = False
        Si encuentra, coloca state='to approve' y usuario_aprobacion_id.
        """
        AdminSetting = self.env['config.settings.approval.po.admin'].sudo()
        handled_any = False

        for order in self:
            es_admin = bool(getattr(order, 'es_admin', False) or getattr(order, 'es_orden_administrativa', False))
            es_presi = bool(getattr(order, 'es_presidencia', False) or getattr(order, 'es_orden_presidencia', False))
            if not (es_admin or es_presi):
                continue
            if order.state not in ('draft', 'sent', 'control_presupuesto'):
                continue

            amount_base = order.amount_untaxed or 0.0
            solicitante_id = (
                (getattr(order, 'solicitante_id', False) and order.solicitante_id.id) or
                (getattr(order, 'solicitante', False) and order.solicitante.id) or
                False
            )

            # Dominio base por rango
            base_domain = [
                ('monto_desde', '<=', amount_base),
                ('monto_hasta', '>=', amount_base),
            ]
            # Filtros opcionales si existen en el modelo
            if 'company_id' in AdminSetting._fields:
                base_domain.append(('company_id', '=', order.company_id.id))
            if 'estado' in AdminSetting._fields:
                base_domain.append(('estado', '=', 'activo'))

            rec = False

            # 1) rango + creador == solicitante
            if solicitante_id and 'usuario_creador' in AdminSetting._fields:
                rec = AdminSetting.search(base_domain + [('usuario_creador', '=', solicitante_id)],
                                        order='monto_desde asc', limit=1)

            # 2) si no hay, rango + creador vacío
            if not rec:
                if 'usuario_creador' in AdminSetting._fields:
                    rec = AdminSetting.search(base_domain + [('usuario_creador', '=', False)],
                                            order='monto_desde asc', limit=1)
                else:
                    # si el modelo no tiene usuario_creador, caer al rango puro
                    rec = AdminSetting.search(base_domain, order='monto_desde asc', limit=1)

            if not rec and order.amount_untaxed > 0:
                raise UserError(_("No hay parámetros de aprobación para el monto %s (ni con creador=solicitante ni con creador vacío).") % amount_base)

            approver_id = rec.usuario_id.id if rec.usuario_id else False
            if not approver_id:
                raise UserError(_("El registro encontrado no tiene 'Usuario Aprobador' configurado."))

            order.write({
                'state': 'to approve',
                'usuario_aprobacion_id': approver_id,
            })
            try:
                order.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=approver_id,
                    summary=_('Aprobar OC (Administrativa/Presidencia)'),
                    note=_('Orden %s requiere tu aprobación. Monto (base): %s') % (order.name or '', amount_base),
                )
            except Exception:
                pass

            if order.partner_id and order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])

            handled_any = True

        return handled_any

    def _is_admin_o_presi(self):
        self.ensure_one()
        return bool(
            getattr(self, 'es_admin', False) or
            getattr(self, 'es_orden_administrativa', False) or
            getattr(self, 'es_presidencia', False) or
            getattr(self, 'es_orden_presidencia', False)
        )
    
    def button_approve(self, force=False):
        for order in self:
            # Si el total es 0, aprobar directo
            if order.amount_total == 0:
                order.write({'state': 'purchase'})
                continue
            if order._is_admin_o_presi():
                amount_base = order.amount_untaxed or 0.0
                target_user_id = order.usuario_aprobacion_id.id or False
                if not target_user_id:
                    rec = self.env['config.settings.approval.po.admin'].sudo().search([
                        ('monto_desde', '<=', amount_base),
                        ('monto_hasta', '>=', amount_base),
                    ], order='monto_desde asc', limit=1)
                    target_user_id = rec.usuario_id.id if rec and rec.usuario_id else False

                if not target_user_id:
                    raise UserError(_("No existe configurado un aprobador para el monto base %s en OC Administrativa/Presidencia.") % amount_base)

                if self.env.user.id != target_user_id:
                    name = self.env['res.users'].browse(target_user_id).name
                    raise UserError(_("Solo el usuario configurado (%s) puede aprobar esta Orden de Compra.") % name)

        return super(PurchaseOrder, self).button_approve(force=force)
    
    def button_approveOld(self, force=False):
        """
        Restringe la aprobación de OC Administrativas/Presidencia al usuario
        configurado en config.settings.approval.po.admin para el rango del monto.
        """
        for order in self:
            if order._is_admin_o_presi():
                amount_base = order.amount_untaxed or 0.0

                # Si no está seteado en la OC, recalcula desde la tabla por si cambió
                target_user_id = order.usuario_aprobacion_id.id or False
                if not target_user_id:
                    approver_id, _req, _creador = order._get_admin_po_approver(amount_base)
                    target_user_id = approver_id

                if not target_user_id:
                    raise UserError(_(
                        "No existe configurado un aprobador para el monto base %s en OC Administrativa/Presidencia."
                    ) % amount_base)

                if self.env.user.id != target_user_id:
                    name = self.env['res.users'].browse(target_user_id).name
                    raise UserError(_("Solo el usuario configurado (%s) puede aprobar esta Orden de Compra.") % name)

        # Si pasa el candado o no es admin/presi, continúa flujo estándar
        return super(PurchaseOrder, self).button_approve(force=force)

    # Sobreescribe la lista de selección para establecer el orden deseado
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(PurchaseOrder, self).fields_get(allfields, attributes)
        if 'state' in res and 'selection' in res['state']:
            # Reorganizar los estados en el orden deseado
            res['state']['selection'] = [
                ('draft', 'SdP'),
                ('control_presupuesto', 'Control Presupuesto'),
                ('financiero', 'Financiero'),
                ('sent', 'SDP Enviada'),
                ('to approve', 'Para aprobar'),
                ('purchase', 'Orden de compra'),
                ('done', 'Bloqueada'),
                ('cancel', 'Cancelado'),
            ]
        return res