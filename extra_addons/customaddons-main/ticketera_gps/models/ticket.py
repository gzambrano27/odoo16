from odoo import api, fields, models, _
from odoo.exceptions import UserError
import pytz

class TicketGps(models.Model):
    _name = 'ticket.gps'
    _description = 'Ticket GPS'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Código', readonly=True, copy=False)
    creation_date = fields.Datetime(
        string='Fecha/Hora Creación',
        default=lambda self: fields.Datetime.now(),
        readonly=True
    )
    asunto = fields.Char(string='Asunto')

    creator_id = fields.Many2one(
        'res.users',
        string='Creador',
        default=lambda self: self.env.user,
        readonly=True
    )

    encargado = fields.Many2one('hr.employee', string='Encargado', tracking=True)
    encargado_user_id = fields.Many2one('res.users', related='encargado.user_id', store=False)

    delegacion_a = fields.Many2one('hr.employee', string='Delegación a')
    delegacion_a_user_id = fields.Many2one('res.users', related='delegacion_a.user_id', store=False)

    delegar_personal = fields.Boolean(string='Delegar Personal')

    department_id = fields.Many2one(
        'hr.department',
        string='Departamento',
        readonly=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        readonly=True
    )
    user_name = fields.Char(
        string='Nombre de Usuario',
        readonly=True
    )

    email = fields.Char(
        string='Correo',
        readonly=True
    )

    phone = fields.Char(
        string='Teléfono',
        readonly=True
    )

    cc = fields.Many2many('hr.employee', string='Cc', tracking=True)
    description = fields.Html(string='Descripción', tracking=True)
    resultado = fields.Html(string='Resultado', tracking=True)

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('sent', 'Enviado'),
        ('progress', 'En Proceso'),
        ('done', 'Finalizado'),
    ], default='draft', tracking=True)

    date_sent = fields.Datetime(readonly=True)
    date_progress = fields.Datetime(readonly=True)
    date_done = fields.Datetime(readonly=True)


    is_encargado_user = fields.Boolean(compute='_compute_is_encargado_user', store=False)

    # Botones
    show_send_button = fields.Boolean(compute='_compute_show_send_button')
    show_return_draft_button = fields.Boolean(compute='_compute_show_return_draft_button')
    show_assigned_buttons = fields.Boolean(compute='_compute_show_assigned_buttons')

    sending_user_id = fields.Many2one('res.users', readonly=True, string='Usuario que envía')

    resultado_readonly = fields.Boolean(compute='_compute_resultado_readonly', store=True)

    color_state = fields.Selection(
        [('creator', 'Creador'),
         ('assigned', 'Encargado'),
         ('cc', 'Copia'),
         ('delegado', 'delegado'),
         ('none', 'Nada')],
        compute='_compute_color_state',
        store=False
    )

    def write(self, vals):
        # Detectar si se está llenando el campo 'resultado'
        enviar_correo = False
        for rec in self:
            if 'resultado' in vals and vals['resultado'] and not rec.resultado:
                enviar_correo = True

        result = super().write(vals)

        # Si corresponde, enviar notificación de finalización al creador
        if enviar_correo:
            for rec in self.filtered(lambda r: r.state == 'done' and r.creator_id and r.creator_id.partner_id.email):
                mail_vals = {
                    'subject': (rec.asunto or "Ticket sin asunto") + " - Ticket Finalizado",
                    'email_to': rec.creator_id.partner_id.email,
                    'body_html': f"""
                        <p>Estimad@ <strong>{rec.creator_id.name}</strong>,</p>
                        <p>El <strong>{rec.name}</strong> ha sido Finalizado.</p>
                        <p><strong>Resultado:</strong><br/>
                           {rec.resultado or '<em>Sin resultado</em>'}
                        </p>
                    """,
                }
                rec._send_mail_custom(mail_vals)

        return result

    # -------------------------------------------------------------------------
    # Cómputos
    # -------------------------------------------------------------------------
    @api.depends('encargado_user_id')
    def _compute_is_encargado_user(self):
        """True si usuario actual == encargado.user_id."""
        for rec in self:
            rec.is_encargado_user = (rec.encargado_user_id.id == rec.env.uid)

    @api.depends('creator_id')
    def _compute_show_send_button(self):
        for rec in self:
            rec.show_send_button = (rec.creator_id.id == rec.env.uid)

    @api.depends('creator_id', 'state')
    def _compute_show_return_draft_button(self):
        for rec in self:
            rec.show_return_draft_button = (
                rec.creator_id.id == rec.env.uid
                and rec.state == 'sent'
            )

    @api.depends('encargado', 'delegacion_a')
    def _compute_show_assigned_buttons(self):
        """
        Botones "En Proceso" / "Finalizar" => si user es Encargado o Delegado
        """
        for rec in self:
            can_assign = False
            if rec.encargado and rec.encargado.user_id and rec.encargado.user_id.id == rec.env.uid:
                can_assign = True
            elif rec.delegacion_a and rec.delegacion_a.user_id and rec.delegacion_a.user_id.id == rec.env.uid:
                can_assign = True
            rec.show_assigned_buttons = can_assign

    @api.depends('resultado', 'state', 'show_assigned_buttons')
    def _compute_resultado_readonly(self):
        """
        - En done => se puede llenar solo si está vacío y user es Encargado/Delegado
        - Sino => readonly = True
        """
        for rec in self:
            ro = True
            if rec.state == 'done' and not rec.resultado and rec.show_assigned_buttons:
                ro = False
            rec.resultado_readonly = ro

    @api.depends('creator_id', 'encargado', 'cc')
    def _compute_color_state(self):
        for rec in self:
            user_id = self.env.uid

            # 1) Si es tuyo como creador
            if rec.creator_id.id == user_id:
                rec.color_state = 'creator'

            # 2) else si eres el encargado
            elif rec.encargado and rec.encargado.user_id.id == user_id:
                rec.color_state = 'assigned'

            # 3) else si estás en cc
            elif any(emp.user_id.id == user_id for emp in rec.cc):
                rec.color_state = 'cc'

            elif any(emp.user_id.id == user_id for emp in rec.delegacion_a):
                rec.color_state = 'delegado'
            # 4) si no cumples nada
            else:
                rec.color_state = 'none'

    # -------------------------------------------------------------------------
    # Creación y Onchange
    # -------------------------------------------------------------------------
    @api.model
    def create(self, vals):
        if not vals.get('name'):
            seq = self.env['ir.sequence'].next_by_code('ticket.gps')
            vals['name'] = seq or 'TICKET-0000'
        return super().create(vals)

    @api.onchange('encargado')
    def _onchange_encargado(self):
        """Completa departamento, compañía, etc."""
        if self.encargado:
            self.department_id = self.encargado.department_id.id
            self.company_id = self.encargado.company_id.id
            self.user_name = self.encargado.name
            self.email = self.encargado.work_email
            self.phone = self.encargado.work_phone

    def _update_fields_from_encargado(self):
        for rec in self:
            if rec.encargado:
                rec.write({
                    'department_id': rec.encargado.department_id.id,
                    'company_id': rec.encargado.company_id.id,
                    'user_name': rec.encargado.name,
                    'email': rec.encargado.work_email,
                    'phone': rec.encargado.work_phone,
                })

    # -------------------------------------------------------------------------
    # Transiciones de estado
    # -------------------------------------------------------------------------
    def action_send(self):
        """Borrador -> Enviado. Envía correos."""
        self.ensure_one()
        if self.creator_id.id != self.env.uid:
            raise UserError(_("Solo el usuario que creó este ticket puede enviarlo."))

        self.sending_user_id = self.env.user
        self._update_fields_from_encargado()
        self.write({'state': 'sent', 'date_sent': fields.Datetime.now()})

        # Correo al Encargado
        if self.encargado and self.encargado.work_email:
            mail_vals_enc = {
                'subject': (self.asunto or "Ticket sin asunto") + " - Ticket Nuevo",
                'email_to': self.encargado.work_email,
                'body_html': f"""
                    <p>Estimad@ <strong>{self.encargado.name}</strong>,</p>
                    <p>El <strong>{self.name}</strong> se le ha sido asignado.</p>
                    <p><strong>Descripción:</strong><br/>
                       {self.description or '<em>Sin descripción</em>'}
                    </p>
                """,
            }
            self._send_mail_custom(mail_vals_enc)

        # CC
        cc_mails = ",".join(emp.work_email for emp in self.cc if emp.work_email)
        if cc_mails:
            encargado_name = self.encargado.name if self.encargado else 'N/A'
            mail_vals_cc = {
                'subject': (self.asunto or "Ticket sin asunto") + " - Ticket Nuevo (Copia)",
                'email_to': cc_mails,
                'body_html': f"""
                    <p>Estimad@s {", ".join(emp.name for emp in self.cc)},</p>
                    <p>El <strong>{self.name}</strong> se le ha sido asignado.</p>
                    <p><strong>Encargado:</strong> {encargado_name}</p>
                    <p><strong>Descripción:</strong><br/>
                       {self.description or '<em>Sin descripción</em>'}
                    </p>
                """,
            }
            self._send_mail_custom(mail_vals_cc)

    def action_draft(self):
        """Enviado -> Borrador."""
        self.ensure_one()
        if self.creator_id.id != self.env.uid:
            raise UserError(_("Solo el usuario que creó este ticket puede volverlo a Borrador."))
        self.write({'state': 'draft'})
        return True

    def action_progress(self):
        """
        Enviado -> En Proceso => (Encargado o Delegado).
        Envía correo al Creador de que ya está en Proceso.
        """
        self.ensure_one()
        if not self.show_assigned_buttons:
            raise UserError(_("Solo el Encargado o Delegado puede ponerlo en proceso."))
        if self.state != 'sent':
            raise UserError(_("El ticket debe estar en 'Enviado' para pasarlo a 'En Proceso'."))

        self._update_fields_from_encargado()
        self.write({'state': 'progress', 'date_progress': fields.Datetime.now()})

        # Correo al Creador
        if self.creator_id and self.creator_id.partner_id.email:
            mail_vals_cr = {
                'subject': (self.asunto or "Ticket sin asunto") + " - Ticket en Proceso",
                'email_to': self.creator_id.partner_id.email,
                'body_html': f"""
                    <p>Estimad@ <strong>{self.creator_id.name}</strong>,</p>
                    <p>El <strong>{self.name}</strong> ahora está en estado <strong>En Proceso</strong>.</p>
                """,
            }
            self._send_mail_custom(mail_vals_cr)

    def action_done(self):
        """
        Progreso -> Finalizado => (Encargado o Delegado).
        (No se envía correo automático).
        """
        self.ensure_one()
        if not self.show_assigned_buttons:
            raise UserError(_("Solo el Encargado o Delegado puede finalizarlo."))
        if self.state != 'progress':
            raise UserError(_("El ticket debe estar en 'En Proceso' para poder finalizarlo."))

        self._update_fields_from_encargado()
        self.write({'state': 'done', 'date_done': fields.Datetime.now()})

    # ------------------ Notificar Delegado -------------------
    def action_notify_delegado(self):
        """
        Asunto => "... - Delegación de Ticket"
        Sólo el Encargado (is_encargado_user).
        """
        self.ensure_one()
        if self.state not in ('progress','done'):
            raise UserError(_("Solo se puede delegar en estado 'En Proceso' o 'Finalizado'."))

        if not self.is_encargado_user:
            raise UserError(_("Solo el Encargado puede notificar al Delegado."))
        if not self.delegar_personal:
            raise UserError(_("Debe marcar 'Delegar Personal' antes de enviar notificación."))
        if not self.delegacion_a or not self.delegacion_a.work_email:
            raise UserError(_("No hay 'Delegación a' con correo para notificar."))

        mail_vals = {
            'subject': (self.asunto or "Ticket sin asunto") + " - Delegación de Ticket",
            'email_to': self.delegacion_a.work_email,
            'body_html': f"""
                <p>Estimad@ <strong>{self.delegacion_a.name}</strong>,</p>
                <p>Se le ha delegado parte del <strong>{self.name}</strong> a su persona.</p>
                <p><strong>Asunto:</strong> {self.asunto or ''}</p>
                <p><strong>Descripción:</strong><br/>
                   {self.description or '<em>Sin descripción</em>'}
                </p>
            """,
        }
        self._send_mail_custom(mail_vals)

    # ------------------ Finalizado => Notificar CC y Encargado -------------------
    def action_notify_final_cc(self):
        """
        En done => "Ticket Finalizado (Copia)"
        """
        self.ensure_one()
        if self.state != 'done':
            raise UserError(_("El ticket debe estar en 'Finalizado' para notificar CC."))

        cc_mails = ",".join(emp.work_email for emp in self.cc if emp.work_email)
        if cc_mails:
            mail_vals_cc = {
                'subject': (self.asunto or "Ticket sin asunto") + " - Ticket Finalizado (Copia)",
                'email_to': cc_mails,
                'body_html': f"""
                    <p>Estimad@s {", ".join(emp.name for emp in self.cc)},</p>
                    <p>El <strong>{self.name}</strong> ha sido Finalizado.</p>
                    <p><strong>Resultado:</strong><br/>
                       {self.resultado or '<em>Sin resultado</em>'}
                    </p>
                """,
            }
            self._send_mail_custom(mail_vals_cc)

    def action_notify_final_encargado(self):
        """
        En done => "Ticket Finalizado"
        """
        self.ensure_one()
        if self.state != 'done':
            raise UserError(_("El ticket debe estar en 'Finalizado' para notificar al Encargado."))

        if self.encargado and self.encargado.work_email:
            mail_vals_enc = {
                'subject': (self.asunto or "Ticket sin asunto") + " - Ticket Finalizado",
                'email_to': self.encargado.work_email,
                'body_html': f"""
                    <p>Estimad@ <strong>{self.encargado.name}</strong>,</p>
                    <p>El <strong>{self.name}</strong> ha sido Finalizado.</p>
                    <p><strong>Resultado:</strong><br/>
                       {self.resultado or '<em>Sin resultado</em>'}
                    </p>
                """,
            }
            self._send_mail_custom(mail_vals_enc)

    # -------------------------------------------------------------------------
    # UTILS
    # -------------------------------------------------------------------------
    def _get_ticket_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/web#id={self.id}&model=ticket.gps&view_type=form"

    def _send_mail_custom(self, mail_vals):
        # Enviar el correo
        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)
        
        # Obtener la fecha y hora actual en UTC y convertirla a la zona horaria local
        current_datetime = fields.Datetime.now()
        current_datetime_local = pytz.utc.localize(current_datetime).astimezone(local_tz)
        """
        Botón “Ver Ticket” (rojo #8B0000, letras blancas).
        Footer => "Mensaje automático - Tickets GPS Group".
        """
        partial_content = mail_vals.get('body_html','')
        subject = mail_vals.get('subject','Notificación de Ticket')
        recipient = mail_vals.get('email_to','')

        sender_user = self.sending_user_id or self.env.user
        if self.state=='done':
            detail_info = f"""
            <p><strong>Fecha/Hora Finalizacion:</strong> {pytz.utc.localize(self.date_done).astimezone(local_tz).strftime('%d/%m/%Y %H:%M')}</p>
            """
            partial_content = partial_content + detail_info
        else:
            detail_info = f"""
            <p><strong>Enviado por:</strong> {sender_user.name}</p>
            <p><strong>Fecha/Hora:</strong> {current_datetime_local.strftime('%d/%m/%Y %H:%M')}</p>
            """

            partial_content = detail_info + partial_content

        wrapped_html = f"""
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
                background-color: #8B0000;
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
              .button-link {{
                display:inline-block;
                background: #8B0000;
                color:#FFF !important;
                padding:10px 15px;
                text-decoration:none !important;
                border-radius:4px;
                margin-top:20px;
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
                <h2>Notificación de Ticket</h2>
              </div>
              <div class="email-body">
                {partial_content}
                <p style="margin-top:20px;">
                  <a href="{self._get_ticket_url()}" class="button-link"
                     style="color:#FFF !important;text-decoration:none !important;"
                  >
                    Ver Ticket
                  </a>
                </p>
              </div>
              <div class="email-footer">
                <p>Mensaje automático - Tickets GPS Group</p>
              </div>
            </div>
          </body>
        </html>
        """

        mail = self.env['mail.mail'].sudo().create({
            'subject': subject,
            'body_html': wrapped_html,
            'email_to': recipient,
            'auto_delete': False,
            'author_id': self.env.user.partner_id.id,
        })
        mail.send()
