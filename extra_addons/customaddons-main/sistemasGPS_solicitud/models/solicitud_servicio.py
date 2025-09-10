# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError

class SolicitudServicio(models.Model):
    _name = 'solicitud.servicio'
    _description = 'Solicitud de Servicio'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    @api.model
    def _default_employee_id(self):
        """Retorna el empleado relacionado con el usuario actual."""
        user = self.env.user
        return self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)

    name = fields.Char(
        string='Número de Solicitud',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    date_solicitud = fields.Date(
        string='Fecha de Solicitud',
        default=fields.Date.today,
        required=True
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Departamento Solicitante',
        required=True,
        default=lambda self: self.env.user.employee_id.department_id
    )
    solicitante_id = fields.Many2one(
        'hr.employee',
        string='Empleado Solicitante',
        default=_default_employee_id,
        required=True,
        readonly=True
    )
    jefe_directo_id = fields.Many2one('hr.employee', string='Jefe Directo')

    service_requested = fields.Selection([
        ('nuevo_dsllo', 'Nuevo Desarrollo'),
        ('modificacion', 'Modificación'),
        ('capacitacion', 'Capacitación')
    ], string='Servicio Solicitado', required=True)

    service_type = fields.Selection([
        ('urgente', 'Urgente'),
        ('ordinario', 'Ordinario')
    ], string='Tipo')

    fecha_entrega_estimada = fields.Date(
        string='Fecha de Entrega Estimada',
        copy=False,
        tracking=True
    )
    aceptacion_de_riesgo = fields.Text(
        string="Aceptación de Riesgo",
        help="Indique la aceptación de riesgo"
    )

    solicitante_user_id = fields.Many2one(
        'res.users',
        related='solicitante_id.user_id',
        store=True,
        string="Usuario Solicitante"
    )
    asunto = fields.Text(string="Asunto", required=True)
    description = fields.Html(string='Descripción', required=True)

    check_funciona = fields.Boolean(string="Funciona Correctamente en el Sistema")
    check_no_funciona = fields.Boolean(string="No Funciona Correctamente en el Sistema")
    pruebas_observaciones = fields.Text(string="Observaciones")

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('pending', 'Pendiente de Aprobación'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
        ('in_process', 'En Proceso'),
        ('pruebas', 'Pruebas'),
        ('done', 'Finalizada'),
    ], string='Estado', default='draft', tracking=True)

    boss_id = fields.Many2one('res.users', string='Jefe que aprueba', readonly=True)
    motivo = fields.Html(string="Motivo", help="Motivo del rechazo (cuando la rechazan)")

    #--------------------------------------------------------------------------
    # Onchange
    #--------------------------------------------------------------------------


    @api.onchange('check_funciona')
    def onchange_check_funciona(self):
        if self.check_funciona:
            self.check_no_funciona = False

    @api.onchange('check_no_funciona')
    def onchange_check_no_funciona(self):
        if self.check_no_funciona:
            self.check_funciona = False

    #--------------------------------------------------------------------------
    # Correo
    #--------------------------------------------------------------------------
    def _get_notification_emails(self):
        emails = set()
        if self.jefe_directo_id and self.jefe_directo_id.work_email:
            emails.add(self.jefe_directo_id.work_email)
        if self.solicitante_id and self.solicitante_id.work_email:
            emails.add(self.solicitante_id.work_email)
        if 'correos.primordialesodoo' in self.env:
            for rec in self.env['correos.primordialesodoo'].search([]):
                if rec.email:
                    emails.add(rec.email)
        return emails

    def _send_notification_email(self, subject, body_html_content):
        recipients = self._get_notification_emails()
        if not recipients:
            return
        # Botón de enlace a la solicitud
        solicitud_url = self.get_portal_url()
        link_button = f"""
          <p style="margin-top:20px;">
            <a href="{solicitud_url}"
               style="background: #27AE60; color:#FFF; padding:10px 15px; text-decoration:none; border-radius:4px;">
              Ver Solicitud
            </a>
          </p>
        """

        body_html = f"""
        <html>
          <head>
            <meta charset="utf-8"/>
            <style>
              .email-container {{
                  font-family: Arial, sans-serif;
                  max-width: 600px;
                  margin: 20px auto;
                  border: 1px solid #CCC;
                  border-radius: 5px;
                  overflow: hidden;
                  background: #F8F9FA;
              }}
              .email-header {{
                  background-color: #2E86C1;
                  color: #ffffff;
                  padding: 15px;
                  text-align: center;
              }}
              .email-header h2 {{
                  margin: 0;
                  font-size: 22px;
              }}
              .email-body {{
                  padding: 20px;
                  color: #333;
                  line-height: 1.6;
              }}
              .email-body .highlight {{
                  color: #C0392B;
                  font-weight: bold;
              }}
              .email-footer {{
                  background-color: #ECECEC;
                  text-align: center;
                  font-size: 12px;
                  color: #666;
                  padding: 10px;
              }}
            </style>
          </head>
          <body>
            <div class="email-container">
              <div class="email-header">
                <h2>Notificación de Solicitud</h2>
              </div>
              <div class="email-body">
                {body_html_content}
                {link_button}
              </div>
              <div class="email-footer">
                <p>Mensaje automático - Servicio de Asistencia Odoo</p>
              </div>
            </div>
          </body>
        </html>
        """
        mail = self.env['mail.mail'].create({
            'subject': subject,
            'body_html': body_html,
            'email_to': ",".join(recipients),
            'author_id': self.env.user.partner_id.id,
        })
        mail.send()

    #--------------------------------------------------------------------------
    # Creación
    #--------------------------------------------------------------------------
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('solicitud.servicio') or _('New')
        return super(SolicitudServicio, self).create(vals)

    def get_portal_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return '%s/web#id=%s&model=solicitud.servicio&view_type=form' % (base_url, self.id)

    #--------------------------------------------------------------------------
    # Transiciones de estado
    #--------------------------------------------------------------------------
    def action_submit(self):
        """Borrador -> Pendiente (Correo)"""
        if self.state != 'draft':
            raise UserError(_("Solo se pueden enviar solicitudes en estado 'Borrador'."))
        self.state = 'pending'
        subject = _("Solicitud %s pasa a Pendiente de Aprobación") % self.name
        body_html = _(
            "<h3>Estado: <span class='highlight'>Pendiente de Aprobación</span></h3>"
            "<p>La solicitud <strong>%s</strong> se ha enviado para aprobación.</p>"
            "<p><strong>Asunto:</strong> %s</p>"
            "<p><strong>Descripción:</strong> %s</p>"
        ) % (self.name, self.asunto or "", self.description or "")
        self._send_notification_email(subject, body_html)
        return True

    def action_approve(self):
        """Pendiente -> Aprobada (Correo)"""
        if self.state != 'pending':
            raise UserError(_("La solicitud debe estar en 'Pendiente de Aprobación' para aprobarla."))
        self.state = 'approved'
        self.boss_id = self.env.user

        subject = _("Solicitud %s Aprobada") % self.name
        body_html = _(
            "<h3>Solicitud Aprobada</h3>"
            "<p>La solicitud <strong>%s</strong> ha sido aprobada.</p>"
            "<p>(Ahora se pueden llenar los campos Aceptación de Riesgo y Fecha de Entrega.)</p>"
        ) % self.name
        self._send_notification_email(subject, body_html)
        return True

    def action_reject(self):
        """Pendiente/Aprobada -> Rechazada (sin correo)."""
        if self.state not in ['pending', 'approved']:
            raise UserError(_("Solo se puede rechazar si la solicitud está 'Pendiente' o 'Aprobada'."))

        self.state = 'rejected'
        self.boss_id = self.env.user
        return True

    def action_notify_rejected(self):
        """Botón en 'rejected' que envía correo con 'motivo'."""
        if self.state != 'rejected':
            raise UserError(_("La solicitud no está rechazada."))
        if not self.motivo:
            raise UserError(_("Complete el campo 'Motivo' antes de notificar el rechazo."))

        subject = _("Notificación de Rechazo - Solicitud %s") % self.name
        body_html = _(
            "<h3>Notificación de Rechazo</h3>"
            "<p>La solicitud <strong>%s</strong> fue rechazada.</p>"
            "<p><strong>Motivo/Rechazo:</strong> %s</p>"
        ) % (self.name, self.motivo)
        self._send_notification_email(subject, body_html)
        return True

    def action_start_process(self):
        """Aprobada -> En Proceso (Correo con Acept. y Fecha)."""
        if self.state != 'approved':
            raise UserError(_("Solo se puede iniciar el proceso en solicitudes aprobadas."))

        aceptacion = self.aceptacion_de_riesgo or _("(No llenado)")
        fecha = str(self.fecha_entrega_estimada or _("(No llenado)"))

        self.state = 'in_process'
        subject = _("Solicitud %s en Proceso") % self.name
        body_html = _(
            "<h3>Solicitud en Proceso</h3>"
            "<p>La solicitud <strong>%s</strong> pasa a 'En Proceso'.</p>"
            "<p><strong>Aceptación de Riesgo:</strong> %s<br/>"
            "<strong>Fecha de Entrega Estimada:</strong> %s</p>"
        ) % (self.name, aceptacion, fecha)
        self._send_notification_email(subject, body_html)
        return True

    def action_pruebas(self):
        """En Proceso -> Pruebas (Correo)."""
        if self.state != 'in_process':
            raise UserError(_("Solo se puede pasar a Pruebas desde 'En Proceso'."))

        self.state = 'pruebas'
        subject = _("Solicitud %s en Fase de Pruebas") % self.name
        body_html = _(
            "<h3>Solicitud en Fase de Pruebas</h3>"
            "<p>La solicitud <strong>%s</strong> ha pasado a <em>Pruebas</em>.</p>"
            "<p>Ya puede marcar Funciona/No Funciona y Observaciones.</p>"
        ) % (self.name)
        self._send_notification_email(subject, body_html)
        return True

    def action_done(self):
        """Pruebas -> Finalizada (Correo con info de pruebas)."""
        if self.state != 'pruebas':
            raise UserError(_("Solo se pueden finalizar solicitudes en estado 'Pruebas'."))

        self.state = 'done'
        resultado = _("No marcado")
        if self.check_funciona:
            resultado = _("Sí Funciona Correctamente")
        elif self.check_no_funciona:
            resultado = _("No Funciona Correctamente")

        subject = _("Solicitud %s Finalizada") % self.name
        body_html = _(
            "<h3>Solicitud Finalizada</h3>"
            "<p>La solicitud <strong>%s</strong> fue finalizada.</p>"
            "<p><strong>Resultado de Pruebas:</strong> %s</p>"
            "<p><strong>Observaciones:</strong> %s</p>"
        ) % (self.name, resultado, self.pruebas_observaciones or "")
        self._send_notification_email(subject, body_html)
        return True

    def action_reset_draft(self):
        """Rechazada -> Borrador (solo admin)."""
        if not (self.env.user.has_group('sistemasGPS_solicitudes.group_admin_solicitudes_new') or
                self.env.user.has_group('base.group_system')):
            raise UserError(_("Solo administradores pueden revertir una solicitud rechazada a borrador."))

        if self.state != 'rejected':
            raise UserError(_("Solo se puede volver a Borrador cuando está Rechazada."))

        self.state = 'draft'
        return True

    #--------------------------------------------------------------------------
    # RESTRICCIÓN DE ESCRITURA
    #--------------------------------------------------------------------------
    def write(self, vals):
        """
        Bloquea escritura al usuario 'Usuario de Solicitudes' después de mandar (draft->pending).
        Permite la transición draft->pending, pero no ediciones en otros estados.
        """
        user = self.env.user
        is_simple_user = user.has_group('sistemasGPS_solicitudes.group_usuario_solicitudes_new') and not (
            user.has_group('sistemasGPS_solicitudes.group_jefe_solicitudes_new')
            or user.has_group('sistemasGPS_solicitudes.group_admin_solicitudes_new')
            or user.has_group('base.group_system')
        )

        if is_simple_user:
            for rec in self:
                if rec.id and vals:
                    solo_cambia_a_pending = (
                        len(vals) == 1
                        and 'state' in vals
                        and vals['state'] == 'pending'
                        and rec.state == 'draft'
                    )
                    if not solo_cambia_a_pending:
                        raise UserError(
                            _("No puedes modificar la solicitud después de enviarla (Usuario de Solicitudes).")
                        )
        return super(SolicitudServicio, self).write(vals)
