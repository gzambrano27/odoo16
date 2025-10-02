from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR, SA, SU
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

WEEKDAY_MAP = {'MO': MO, 'TU': TU, 'WE': WE, 'TH': TH, 'FR': FR, 'SA': SA, 'SU': SU}


class MeetingMeeting(models.Model):
    _name = 'meeting.meeting'
    _description = 'Reserva de Reunión'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('reserved', 'Reservado'),
        ('cancelled', 'Cancelado'),
    ], default='draft', tracking=True)
    cancel_reason = fields.Text("Motivo de cancelación")
    color = fields.Integer(string='Color', compute='_compute_color', store=True)
    _COLOR_BY_STATE = {
        'draft': 0, 'reserved': 20, 'cancelled': 21,
    }
    is_user = fields.Boolean(compute='_compute_is_user', store=False)
    name = fields.Char(string='Asunto', required=True, tracking=True)
    organizer_id = fields.Many2one('hr.employee', string='Organizador',
                                   default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)],
                                                                                       limit=1))

    organizer_department_id = fields.Many2one(
        'hr.department',
        string="Departamento del Organizador",
        related='organizer_id.department_id',
        store=True,
        readonly=True
    )

    start_datetime = fields.Datetime(string='Comienza', required=True, tracking=True,
                                     default=lambda self: fields.Datetime.now() + timedelta(days=1))
    start_readonly = fields.Datetime(string='Comienza (RO)', related='start_datetime', readonly=True)
    duration_hours = fields.Selection(selection=[(str(i), f"{i} horas" if i > 1 else "1 hora") for i in range(1, 11)],
                                      string='Duración (h)', default='1')

    duration_float = fields.Float(string="Duración (Horas)", compute='_compute_duration_float', store=True)

    duration_hours_user = fields.Selection(
        selection=[(str(i), f"{i} horas" if i > 1 else "1 hora") for i in range(1, 4)],
        string='Duración',
        compute='_compute_duration_wrappers',
        inverse='_inverse_duration_user',
        store=False,
        groups='meeting_reservation.group_meeting_user',
        default='1'
    )

    duration_hours_admin = fields.Selection(
        selection=[(str(i), f"{i} horas" if i > 1 else "1 hora") for i in range(1, 11)],
        string='Duración',
        compute='_compute_duration_wrappers',
        inverse='_inverse_duration_admin',
        store=False,
        groups='meeting_reservation.group_meeting_admin',
        default='1'
    )

    is_room_responsible = fields.Boolean(compute="_compute_is_room_responsible", store=False)
    end_datetime = fields.Datetime(string='Termina', compute='_compute_end_datetime', store=True, tracking=True)
    stop_readonly = fields.Datetime(string='Termina (RO)', related='end_datetime', readonly=True)
    video_url = fields.Char(string='URL de videollamada')
    room_id = fields.Many2one('meeting.room', string='Sala', tracking=True, required=True)
    description = fields.Html(string='Descripción')
    recurrency = fields.Boolean(string='Recurrente?')
    interval = fields.Integer(string='Repetir cada', default=1)
    rrule_type = fields.Selection(
        [('daily', 'Diaria'), ('weekly', 'Semanal'), ('monthly', 'Mensual'), ('yearly', 'Anual')], string='Unidad')
    mon = fields.Boolean('Lun')
    tue = fields.Boolean('Mar')
    wed = fields.Boolean('Mié')
    thu = fields.Boolean('Jue')
    fri = fields.Boolean('Vie')
    sat = fields.Boolean('Sáb')
    sun = fields.Boolean('Dom')
    end_type = fields.Selection([('count', 'Número de veces'), ('end_date', 'Fecha límite')], string='Finaliza')
    count = fields.Integer(string='Veces')
    until = fields.Date(string='Hasta')
    month_by = fields.Selection([('date', 'Día del mes'), ('day', 'El ...')], string='Modo mensual', default='date')
    day = fields.Integer(string='Día (1-31)')
    byday = fields.Selection([('1', '1º'), ('2', '2º'), ('3', '3º'), ('4', '4º'), ('-1', 'Último')], string='Nº')
    weekday = fields.Selection(
        [('MO', 'Lunes'), ('TU', 'Martes'), ('WE', 'Miércoles'), ('TH', 'Jueves'), ('FR', 'Viernes'), ('SA', 'Sábado'),
         ('SU', 'Domingo')], string='Día sem.')
    allow_external_invites = fields.Boolean(string="¿Desea añadir invitados externos?")

    invitation_ids = fields.One2many('meeting.invitation', 'meeting_id', string='Invitaciones')

    internal_invitation_ids = fields.One2many(
        comodel_name='meeting.invitation',
        inverse_name='meeting_id',
        string="Invitados Internos",
        compute='_compute_invitations_by_type',
        readonly=False
    )

    external_invitation_ids = fields.One2many(
        comodel_name='meeting.invitation',
        inverse_name='meeting_id',
        string="Invitados Externos",
        compute='_compute_invitations_by_type',
        readonly=False
    )

    user_can_manage = fields.Boolean(
        string="El usuario puede gestionar",
        compute='_compute_user_can_manage',
        store=False
    )

    def _compute_user_can_manage(self):
        is_admin = self.env.user.has_group('meeting_reservation.group_meeting_admin')
        for meeting in self:
            is_organizer = meeting.organizer_id and meeting.organizer_id.user_id == self.env.user
            if is_admin or is_organizer:
                meeting.user_can_manage = True
            else:
                meeting.user_can_manage = False

    @api.depends('invitation_ids', 'invitation_ids.personal')
    def _compute_invitations_by_type(self):
        for meeting in self:
            meeting.internal_invitation_ids = meeting.invitation_ids.filtered(lambda r: r.personal == 'internal')
            meeting.external_invitation_ids = meeting.invitation_ids.filtered(lambda r: r.personal == 'external')

    def _process_invitation_vals(self, vals):
        if 'internal_invitation_ids' in vals or 'external_invitation_ids' in vals:
            invitation_commands = vals.get('invitation_ids', [])
            if 'internal_invitation_ids' in vals:
                for command in vals.pop('internal_invitation_ids'):
                    if command[0] == 0 and len(command) > 2:
                        command[2]['personal'] = 'internal'
                    invitation_commands.append(command)
            if 'external_invitation_ids' in vals:
                for command in vals.pop('external_invitation_ids'):
                    if command[0] == 0 and len(command) > 2:
                        command[2]['personal'] = 'external'
                    invitation_commands.append(command)
            vals['invitation_ids'] = invitation_commands

    @api.model_create_multi
    def create(self, vals_list):
        user = self.env.user
        today = fields.Date.context_today(self)
        for vals in vals_list:
            self._process_invitation_vals(vals)
            if user.has_group('meeting_reservation.group_meeting_user'):
                start = vals.get('start_datetime')
                if start:
                    start_d = fields.Datetime.from_string(start).date()
                    if start_d <= today:
                        raise ValidationError(_("Las reuniones para usuarios deben crearse con 1 día de anticipación."))
        recs = super().create(vals_list)
        return recs

    def write(self, vals):
        # Primero se procesan las invitaciones, luego se llama al write original
        self._process_invitation_vals(vals)

        # Lógica de seguridad para el guardado (write)
        is_admin = self.env.user.has_group('meeting_reservation.group_meeting_admin')
        for meeting in self:
            is_organizer = meeting.organizer_id.user_id == self.env.user
            if not is_admin and not is_organizer:
                # Si el usuario no es admin ni organizador, no puede guardar cambios.
                # La regla 'ir.rule' ya previene esto, pero una validación extra aquí es más segura.
                raise ValidationError(_("No tienes permiso para modificar esta reunión."))

        res = super().write(vals)

        # Lógica de negocio después del guardado
        user = self.env.user
        if user.has_group('meeting_reservation.group_meeting_user') and 'start_datetime' in vals:
            today = fields.Date.context_today(self)
            for rec in self:
                if rec.start_datetime and rec.start_datetime.date() <= today:
                    raise ValidationError(
                        _("Las reuniones para usuarios deben reprogramarse con 1 día de anticipación."))
        return res

    @api.depends('state')
    def _compute_color(self):
        for rec in self:
            rec.color = self._COLOR_BY_STATE.get(rec.state, 0)

    def _compute_is_user(self):
        is_user = self.env.user.has_group('meeting_reservation.group_meeting_user')
        for rec in self:
            rec.is_user = bool(is_user)

    def _compute_is_room_responsible(self):
        for rec in self:
            responsible_user = rec.room_id.manager_id.user_id if rec.room_id and rec.room_id.manager_id else False
            rec.is_room_responsible = (responsible_user == self.env.user)

    @api.depends('duration_hours')
    def _compute_duration_wrappers(self):
        for rec in self:
            base = rec.duration_hours or '1'
            rec.duration_hours_user = base if base in {'1', '2', '3'} else '3'
            rec.duration_hours_admin = base if base in {str(i) for i in range(1, 11)} else '1'

    @api.depends('duration_hours')
    def _compute_duration_float(self):
        for rec in self:
            rec.duration_float = float(rec.duration_hours or 0.0)

    def _inverse_duration_user(self):
        for rec in self:
            if rec.duration_hours_user:
                rec.duration_hours = rec.duration_hours_user

    def _inverse_duration_admin(self):
        for rec in self:
            if rec.duration_hours_admin:
                rec.duration_hours = rec.duration_hours_admin

    @api.depends('start_datetime', 'duration_hours')
    def _compute_end_datetime(self):
        for rec in self:
            if rec.start_datetime and rec.duration_hours:
                rec.end_datetime = rec.start_datetime + relativedelta(hours=int(rec.duration_hours))
            else:
                rec.end_datetime = False

    @api.onchange('duration_hours_user')
    def _onchange_duration_hours_user(self):
        if self.duration_hours_user:
            self.duration_hours = self.duration_hours_user

    @api.onchange('duration_hours_admin')
    def _onchange_duration_hours_admin(self):
        if self.duration_hours_admin:
            self.duration_hours = self.duration_hours_admin

    @api.constrains('start_datetime', 'end_datetime')
    def _check_dates(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime and rec.end_datetime <= rec.start_datetime:
                raise ValidationError(_("La hora de fin debe ser posterior a la de inicio."))

    @api.constrains('room_id', 'start_datetime', 'end_datetime', 'state')
    def _check_room_not_double_booked(self):
        for rec in self:
            if rec.room_id and rec.start_datetime and rec.end_datetime and rec.state in ('draft', 'reserved'):
                conflicting = self.env['meeting.meeting'].search([
                    ('id', '!=', rec.id or 0),
                    ('state', '=', 'reserved'),
                    ('room_id', '=', rec.room_id.id),
                    ('start_datetime', '<', rec.end_datetime),
                    ('end_datetime', '>', rec.start_datetime),
                ])
                if conflicting:
                    raise ValidationError(
                        _("La sala '%s' ya está reservada en el intervalo seleccionado.") % rec.room_id.name)

    def _styled_summary_email(self, inner_html, title="Notificación de Reunión"):
        return f"""
              <html>
                <head><meta charset="utf-8"/></head>
                <body style="font-family: Arial, sans-serif; background-color: #E9ECEF; padding: 20px;">
                  <div style="max-width:600px; margin:20px auto;
                              border:1px solid #ccc; border-radius:5px;
                              background:#F8F9FA;">

                    <div style="background:#FFFFFF; color:#8B0000;
                                padding:15px; text-align:center;
                                border-top-left-radius: 5px; border-top-right-radius: 5px;
                                border-bottom: 1px solid #ddd;">
                      <h2 style="margin:0; font-size:22px;">{title}</h2>
                    </div>

                    <div style="padding:20px; color:#333; line-height:1.6;">
                      {inner_html}
                    </div>

                    <div style="background:#ECECEC; text-align:center;
                                font-size:12px; color:#8B0000; padding:10px;
                                border-bottom-left-radius: 5px; border-bottom-right-radius: 5px;">
                      Mensaje automático – Sistema de Reuniones GPS
                    </div>

                  </div>
                </body>
              </html>
              """

    def _get_meeting_details_html(self):
        self.ensure_one()
        status_colors = {
            'draft': '#9e9e9e', 'pending': '#2196f3', 'approved': '#4caf50', 'rejected': '#f44336',
        }
        state_label = dict(self._fields['state'].selection).get(self.state, self.state)
        color = status_colors.get(self.state, '#000')
        link = f"/web#id={self.id}&model=meeting.meeting&view_type=form"
        url_block = ""
        if self.video_url:
            url_block = (
                "<tr>"
                "<td style='padding:6px;border:1px solid #ddd;'><b>URL Videollamada</b></td>"
                f"<td style='padding:6px;border:1px solid #ddd;'><a href='{self.video_url}'>{self.video_url}</a></td>"
                "</tr>"
            )
        return f"""
           <p><b>Estado:</b> <span style="color:{color};font-weight:bold;">{state_label}</span></p>
           <table style="width:100%;border-collapse:collapse;">
             <tr><td style="padding:6px;border:1px solid #ddd;"><b>Asunto</b></td><td style="padding:6px;border:1px solid #ddd;">{self.name or ''}</td></tr>
             <tr><td style="padding:6px;border:1px solid #ddd;"><b>Organizador</b></td><td style="padding:6px;border:1px solid #ddd;">{self.organizer_id.name or ''}</td></tr>
             <tr><td style="padding:6px;border:1px solid #ddd;"><b>Comienza</b></td><td style="padding:6px;border:1px solid #ddd;">{self.start_datetime.strftime("%d/%m/%Y %H:%M") if self.start_datetime else ''}</td></tr>
             <tr><td style="padding:6px;border:1px solid #ddd;"><b>Duración</b></td><td style="padding:6px;border:1px solid #ddd;">{self.duration_hours or ''} horas</td></tr>
             <tr><td style="padding:6px;border:1px solid #ddd;"><b>Termina</b></td><td style="padding:6px;border:1px solid #ddd;">{self.end_datetime.strftime("%d/%m/%Y %H:%M") if self.end_datetime else ''}</td></tr>
             <tr><td style="padding:6px;border:1px solid #ddd;"><b>Sala</b></td><td style="padding:6px;border:1px solid #ddd;">{self.room_id.name or ''}</td></tr>
             {url_block}
             <tr><td style="padding:6px;border:1px solid #ddd;"><b>Descripción</b></td><td style="padding:6px;border:1px solid #ddd;">{self.description or ''}</td></tr>
           </table>
           <div style="text-align:center;margin-top:20px;">
             <a href="{link}" style="display:inline-block;padding:10px 18px;background-color:#8B0000;color:#FFF;text-decoration:none;border-radius:4px;font-weight:bold;">
               Ver Registro
             </a>
           </div>
           """

    def _send_meeting_mail(self, partners, subject, body):
        if not partners: return
        partner_ids = [p.id for p in partners if p]
        if not partner_ids: return

        self.message_post(
            partner_ids=partner_ids,
            subject=subject,
            body=self._styled_summary_email(body),
            message_type='email',
            subtype_xmlid='mail.mt_comment',
        )

    def action_reserve(self):
        self.write({'state': 'reserved'})

    def action_back_to_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        return {
            'name': _('Cancelar Reunión'),
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.cancel.meeting',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_meeting_id': self.id,
            }
        }

    def action_reset_draft(self):
        for rec in self:
            if rec.state == 'pending':
                rec.state = 'draft'

    def action_send_all_invitations(self):
        for meeting in self:
            if not meeting.invitation_ids:
                raise ValidationError(_("No hay invitaciones para enviar."))
            for inv in meeting.invitation_ids:
                inv.action_send_invitation()

    def _generate_recurrences_if_needed(self):
        self.ensure_one()
        if not self.recurrency or not self.start_datetime or not self.end_datetime: return
        base = self
        base_start = base.start_datetime
        base_end = base.end_datetime
        step = self._rrule_step()
        if not step: return
        if self.end_type == 'count' and self.count:
            max_instances = max(self.count - 1, 0)
            until_dt = None
        elif self.end_type == 'end_date' and self.until:
            max_instances = 500
            until_dt = datetime.combine(self.until, base_start.time())
        else:
            return
        created, next_start, next_end = 0, base_start, base_end
        while created < max_instances:
            next_start += step
            next_end += step
            if until_dt and next_start > until_dt: break
            exists = self.search_count([('start_datetime', '=', next_start), ('room_id', '=', base.room_id.id)])
            if not exists:
                self.create({
                    'name': base.name, 'organizer_id': base.organizer_id.id, 'start_datetime': next_start,
                    'duration_hours': base.duration_hours, 'end_datetime': next_end, 'video_url': base.video_url,
                    'room_id': base.room_id.id, 'description': base.description, 'state': 'pending',
                    'recurrency': False,
                })
            created += 1

    def _rrule_step(self):
        n = self.interval or 1
        if self.rrule_type == 'daily': return relativedelta(days=+n)
        if self.rrule_type == 'weekly': return relativedelta(weeks=+n)
        if self.rrule_type == 'monthly':
            if self.month_by == 'day' and self.weekday:
                nth, wk = int(self.byday or '1'), WEEKDAY_MAP.get(self.weekday, None)
                if wk: return relativedelta(months=+n, weekday=wk(nth))
            return relativedelta(months=+n)
        if self.rrule_type == 'yearly': return relativedelta(years=+n)
        return None

    # ==================== INICIO DE LA CORRECCIÓN DEFINITIVA ====================
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(MeetingMeeting, self).fields_get(allfields, attributes)

        is_admin = self.env.user.has_group('meeting_reservation.group_meeting_admin')

        # Si el usuario es administrador, no aplicamos ninguna restricción de solo lectura.
        if is_admin:
            return res

        # Esta lógica se aplica solo cuando se abre un registro existente en la vista de formulario.
        # El contexto `active_id` es la clave para saber qué registro se está viendo.
        if self.env.context.get('active_id'):
            # Usamos `sudo()` para saltar reglas de acceso y poder leer el registro,
            # ya que la regla `ir.rule` podría impedir la lectura inicial.
            record = self.env['meeting.meeting'].sudo().browse(self.env.context.get('active_id'))

            # Comprobamos si el usuario actual es el organizador de la reunión
            is_organizer = record.organizer_id and record.organizer_id.user_id == self.env.user

            # Si el usuario NO es el organizador (y ya sabemos que no es admin),
            # hacemos todos los campos de solo lectura.
            if not is_organizer:
                for field_name in res:
                    res[field_name]['readonly'] = True

        return res

    # ===================== FIN DE LA CORRECCIÓN DEFINITIVA ======================

    @api.onchange('start_datetime', 'duration_hours')
    def _onchange_room_domain(self):
        domain = []
        if self.start_datetime and self.duration_hours:
            end_dt = self.start_datetime + relativedelta(hours=int(self.duration_hours))
            overlapping = self.env['meeting.meeting'].sudo().search([
                ('id', '!=', self._origin.id if self._origin else 0),
                ('state', '=', 'reserved'),
                ('room_id', '!=', False),
                ('start_datetime', '<', end_dt),
                ('end_datetime', '>', self.start_datetime),
            ])
            domain = [('id', 'not in', overlapping.mapped('room_id').ids)]
        return {'domain': {'room_id': domain}}

    def name_get(self):
        result = []
        for rec in self:
            room_name = rec.room_id.name if rec.room_id else _("Sin Sala")
            start_time_str = ""
            end_time_str = ""
            user_tz = self.env.user.tz or 'UTC'

            if rec.start_datetime:
                local_start_time = fields.Datetime.context_timestamp(rec.with_context(tz=user_tz), rec.start_datetime)
                start_time_str = local_start_time.strftime("%H:%M")

            if rec.end_datetime:
                local_end_time = fields.Datetime.context_timestamp(rec.with_context(tz=user_tz), rec.end_datetime)
                end_time_str = local_end_time.strftime("%H:%M")

            display_name = f"{room_name} ({start_time_str} - {end_time_str})"
            result.append((rec.id, display_name))
        return result