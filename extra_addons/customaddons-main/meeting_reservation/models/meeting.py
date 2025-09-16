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
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ], default='draft', tracking=True)

    color = fields.Integer(string='Color', compute='_compute_color', store=True)

    _COLOR_BY_STATE = {
        'draft': 0,       # Gris
        'pending': 4,     # Azul
        'approved': 20,   # Verde
        'rejected': 21,   # Rojo
    }

    @api.depends('state')
    def _compute_color(self):
        for rec in self:
            rec.color = self._COLOR_BY_STATE.get(rec.state, 0)

    is_user = fields.Boolean(compute='_compute_is_user', store=False)

    def _compute_is_user(self):
        is_user = self.env.user.has_group('meeting_reservation.group_meeting_user')
        for rec in self:
            rec.is_user = bool(is_user)

    # -------------------- Detalles de la reunión --------------------
    name = fields.Char(
        string='Asunto', required=True, tracking=True,
        states={'approved': [('readonly', True)], 'rejected': [('readonly', True)]},
    )

    organizer_id = fields.Many2one(
        'hr.employee', string='Organizador',
        default=lambda self: self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1),
        states={'approved': [('readonly', True)], 'rejected': [('readonly', True)]},
    )

    start_datetime = fields.Datetime(
        string='Comienza', required=True, tracking=True,
        default=lambda self: fields.Datetime.now() + timedelta(days=1),
        states={'approved': [('readonly', True)], 'rejected': [('readonly', True)]},
    )
    start_readonly = fields.Datetime(string='Comienza (RO)', related='start_datetime', readonly=True)

    duration_hours = fields.Selection(
        selection=[(str(i), f"{i} horas" if i > 1 else "1 hora") for i in range(1, 11)],
        string='Duración (h)', default='1',
        states={'approved': [('readonly', True)], 'rejected': [('readonly', True)]},
    )

    duration_hours_user = fields.Selection(
        selection=[('1', '1 hora'), ('2', '2 horas'), ('3', '3 horas')],
        string='Duración', default='1', compute='_compute_duration_wrappers',
        inverse='_inverse_duration_user', store=False,
        groups='meeting_reservation.group_meeting_user'
    )
    duration_hours_admin = fields.Selection(
        selection=[(str(i), f"{i} horas" if i > 1 else "1 hora") for i in range(1, 11)],
        string='Duración', default='1', compute='_compute_duration_wrappers',
        inverse='_inverse_duration_admin', store=False,
        groups='meeting_reservation.group_meeting_admin'
    )
    is_room_responsible = fields.Boolean(compute="_compute_is_room_responsible", store=False)

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

    def _inverse_duration_user(self):
        for rec in self:
            if rec.duration_hours_user:
                rec.duration_hours = rec.duration_hours_user

    def _inverse_duration_admin(self):
        for rec in self:
            if rec.duration_hours_admin:
                rec.duration_hours = rec.duration_hours_admin

    end_datetime = fields.Datetime(
        string='Termina', compute='_compute_end', store=True, readonly=True, tracking=True
    )
    stop_readonly = fields.Datetime(string='Termina (RO)', related='end_datetime', readonly=True)

    video_url = fields.Char(
        string='URL de videollamada',
        states={'approved': [('readonly', True)], 'rejected': [('readonly', True)]},
    )

    room_id = fields.Many2one(
        'meeting.room', string='Sala', tracking=True, required=True,
        states={'approved': [('readonly', True)], 'rejected': [('readonly', True)]},
    )

    description = fields.Html(
        string='Descripción',
        states={'approved': [('readonly', True)], 'rejected': [('readonly', True)]},
    )

    invitation_ids = fields.One2many('meeting.invitation', 'meeting_id', string='Invitaciones')

    # -------------------- Recurrencia --------------------
    recurrency = fields.Boolean(string='Recurrente?')
    interval = fields.Integer(string='Repetir cada', default=1)
    rrule_type = fields.Selection(
        [('daily', 'Diaria'), ('weekly', 'Semanal'),
         ('monthly', 'Mensual'), ('yearly', 'Anual')],
        string='Unidad'
    )

    mon = fields.Boolean('Lun')
    tue = fields.Boolean('Mar')
    wed = fields.Boolean('Mié')
    thu = fields.Boolean('Jue')
    fri = fields.Boolean('Vie')
    sat = fields.Boolean('Sáb')
    sun = fields.Boolean('Dom')

    end_type = fields.Selection(
        [('count', 'Número de veces'), ('end_date', 'Fecha límite')],
        string='Finaliza'
    )
    count = fields.Integer(string='Veces')
    until = fields.Date(string='Hasta')

    month_by = fields.Selection(
        [('date', 'Día del mes'), ('day', 'El ...')],
        string='Modo mensual', default='date'
    )
    day = fields.Integer(string='Día (1-31)')
    byday = fields.Selection(
        [('1', '1º'), ('2', '2º'), ('3', '3º'), ('4', '4º'), ('-1', 'Último')],
        string='Nº'
    )
    weekday = fields.Selection(
        [('MO', 'Lunes'), ('TU', 'Martes'), ('WE', 'Miércoles'),
         ('TH', 'Jueves'), ('FR', 'Viernes'), ('SA', 'Sábado'), ('SU', 'Domingo')],
        string='Día sem.'
    )

    # -------------------- FIN automático + dominio de salas --------------------
    @api.depends('start_datetime', 'duration_hours')
    def _compute_end(self):
        for rec in self:
            if rec.start_datetime and rec.duration_hours:
                rec.end_datetime = rec.start_datetime + relativedelta(hours=int(rec.duration_hours))
            else:
                rec.end_datetime = False

    @api.onchange('start_datetime', 'duration_hours',
                  'duration_hours_user', 'duration_hours_admin')
    def _onchange_dates_and_room_domain(self):
        for rec in self:
            if rec.start_datetime and rec.duration_hours:
                rec.end_datetime = rec.start_datetime + relativedelta(hours=int(rec.duration_hours))

            domain = []
            if rec.start_datetime and rec.end_datetime:
                # ⚠️ Solo bloquear salas si hay reunión aprobada
                overlapping = self.env['meeting.meeting'].sudo().search([
                    ('id', '!=', rec.id or 0),
                    ('state', '=', 'approved'),
                    ('room_id', '!=', False),
                    ('start_datetime', '<', rec.end_datetime),
                    ('end_datetime', '>', rec.start_datetime),
                ])
                domain = [('id', 'not in', overlapping.mapped('room_id').ids)]
            return {'domain': {'room_id': domain}}

    # -------------------- Validaciones --------------------
    @api.constrains('start_datetime', 'end_datetime')
    def _check_dates(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime and rec.end_datetime <= rec.start_datetime:
                raise ValidationError(_("La hora de fin debe ser posterior a la de inicio."))

    @api.constrains('room_id', 'start_datetime', 'end_datetime', 'state')
    def _check_room_not_double_booked(self):
        for rec in self:
            if rec.room_id and rec.start_datetime and rec.end_datetime and rec.state in ('draft', 'pending', 'approved'):
                conflicting = self.env['meeting.meeting'].search([
                    ('id', '!=', rec.id or 0),
                    ('state', '!=', 'rejected'),
                    ('room_id', '=', rec.room_id.id),
                    ('start_datetime', '<', rec.end_datetime),
                    ('end_datetime', '>', rec.start_datetime),
                ])
                if conflicting:
                    raise ValidationError(_("La sala '%s' ya está reservada en el intervalo seleccionado.") % rec.room_id.name)

    # -------------------- Restricciones usuarios --------------------
    @api.model_create_multi
    def create(self, vals_list):
        user = self.env.user
        today = fields.Date.context_today(self)
        for vals in vals_list:
            if user.has_group('meeting_reservation.group_meeting_user'):
                start = vals.get('start_datetime')
                if start:
                    start_d = fields.Datetime.from_string(start).date()
                    if start_d <= today:
                        raise ValidationError(_("Las reuniones para usuarios deben crearse con 1 día de anticipación."))
        recs = super().create(vals_list)
        return recs

    def write(self, vals):
        res = super().write(vals)
        user = self.env.user
        if user.has_group('meeting_reservation.group_meeting_user') and 'start_datetime' in vals:
            today = fields.Date.context_today(self)
            for rec in self:
                if rec.start_datetime and rec.start_datetime.date() <= today:
                    raise ValidationError(_("Las reuniones para usuarios deben reprogramarse con 1 día de anticipación."))
        return res

        # -------------------- Emails --------------------

    def _styled_summary_email(self, inner_html, title="Notificación de Reunión"):
        return f"""
           <html>
             <head><meta charset="utf-8"/></head>
             <body style="font-family: Arial, sans-serif; background:#F8F9FA; padding:20px;">
               <div style="max-width:650px;margin:20px auto;border:1px solid #ccc;border-radius:6px;background:#FFFFFF;">
                 <div style="background:#8B0000;color:#FFF;padding:15px;text-align:center;border-top-left-radius:6px;border-top-right-radius:6px;">
                   <h2 style="margin:0;font-size:22px;">{title}</h2>
                 </div>
                 <div style="padding:20px;color:#333;line-height:1.6;">
                   {inner_html}
                 </div>
                 <div style="background:#ECECEC;text-align:center;font-size:12px;color:#666;padding:10px;border-bottom-left-radius:6px;border-bottom-right-radius:6px;">
                   Mensaje automático – Sistema de Reuniones GPS
                 </div>
               </div>
             </body>
           </html>
           """

    def _get_meeting_details_html(self):
        self.ensure_one()
        status_colors = {
            'draft': '#9e9e9e',
            'pending': '#2196f3',
            'approved': '#4caf50',
            'rejected': '#f44336',
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
        if not partners:
            return
        emails = [p.email for p in partners if p.email]
        if not emails:
            return
        mail_values = {
            'subject': subject,
            'body_html': self._styled_summary_email(body),
            'email_to': ",".join(emails),
            'author_id': self.env.user.partner_id.id,
        }
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()

    # -------------------- Acciones --------------------
    def action_to_pending(self):
        for rec in self:
            rec.state = 'pending'
            if rec.room_id.manager_id and rec.room_id.manager_id.user_id:
                html = rec._get_meeting_details_html()
                rec._send_meeting_mail(
                    rec.room_id.manager_id.user_id.partner_id,
                    f"Reunión pendiente: {rec.name}", html
                )

    def action_approve(self):
        for rec in self:
            rec.state = 'approved'
            if rec.organizer_id and rec.organizer_id.user_id:
                html = rec._get_meeting_details_html()
                rec._send_meeting_mail(
                    rec.organizer_id.user_id.partner_id,
                    f"Reunión aprobada: {rec.name}", html
                )

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'
            if rec.organizer_id and rec.organizer_id.user_id:
                html = rec._get_meeting_details_html()
                rec._send_meeting_mail(
                    rec.organizer_id.user_id.partner_id,
                    f"Reunión rechazada: {rec.name}", html
                )

    def action_reset_draft(self):
        for rec in self:
            if rec.state == 'pending':
                rec.state = 'draft'


    def action_send_all_invitations(self):
        for rec in self:
            for inv in rec.invitation_ids:
                inv.action_send_invitation()

    def action_send_invitation(self):
        for rec in self:
            for inv in rec.invitation_ids:
                if inv.employee_id and inv.employee_id.user_id:
                    html = f"<p><b>Invitación a la reunión:</b></p>" + rec._get_meeting_details_html()
                    rec._send_meeting_mail(
                        inv.employee_id.user_id.partner_id,
                        f"Invitación a reunión: {rec.name}",
                        html
                    )
                inv.invitation_sent = True

    # -------------------- Recurrencias --------------------
    def _generate_recurrences_if_needed(self):
        self.ensure_one()
        if not self.recurrency or not self.start_datetime or not self.end_datetime:
            return

        base = self
        base_start = base.start_datetime
        base_end = base.end_datetime
        step = self._rrule_step()
        if not step:
            return

        if self.end_type == 'count' and self.count:
            max_instances = max(self.count - 1, 0)
            until_dt = None
        elif self.end_type == 'end_date' and self.until:
            max_instances = 500
            until_dt = datetime.combine(self.until, base_start.time())
        else:
            return

        created = 0
        next_start = base_start
        next_end = base_end

        while created < max_instances:
            next_start += step
            next_end += step
            if until_dt and next_start > until_dt:
                break

            exists = self.search_count([
                ('start_datetime', '=', next_start),
                ('room_id', '=', base.room_id.id),
            ])
            if not exists:
                self.create({
                    'name': base.name,
                    'organizer_id': base.organizer_id.id,
                    'start_datetime': next_start,
                    'duration_hours': base.duration_hours,
                    'end_datetime': next_end,
                    'video_url': base.video_url,
                    'room_id': base.room_id.id,
                    'description': base.description,
                    'state': 'pending',
                    'recurrency': False,
                })
            created += 1

    def _rrule_step(self):
        n = self.interval or 1
        if self.rrule_type == 'daily':
            return relativedelta(days=+n)
        if self.rrule_type == 'weekly':
            return relativedelta(weeks=+n)
        if self.rrule_type == 'monthly':
            if self.month_by == 'day' and self.weekday:
                nth = int(self.byday or '1')
                wk = WEEKDAY_MAP.get(self.weekday, None)
                if wk:
                    return relativedelta(months=+n, weekday=wk(nth))
            return relativedelta(months=+n)
        if self.rrule_type == 'yearly':
            return relativedelta(years=+n)
        return None