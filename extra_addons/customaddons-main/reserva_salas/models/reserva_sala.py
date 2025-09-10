from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class ReservaSala(models.Model):
    _name = 'reserva.sala'
    _description = 'Reserva de Sala de Reuniones'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Código de Reserva', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    sala_id = fields.Many2one('sala.reunion', string='Sala', required=True)
    motivo = fields.Text(string='Motivo', required=True)
    fecha_desde = fields.Datetime(string='Fecha Desde', required=True)
    fecha_hasta = fields.Datetime(string='Fecha Hasta', required=True)
    empleado_responsable_id = fields.Many2one('hr.employee', string='Responsable',
                                              default=lambda self: self.env.user.employee_id, readonly=True)
    empleados_invitados_ids = fields.Many2many('hr.employee', string='Personal Invitado')
    duracion = fields.Char(string='Duración', compute='_compute_duracion', store=True, readonly=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('pending', 'Pendiente de Aprobación'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
    ], string='Estado', default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('reserva.sala') or _('New')
        return super(ReservaSala, self).create(vals)

    def action_submit(self):
        if self.state != 'draft':
            raise ValidationError(_("Solo se pueden enviar reservas en estado 'Borrador'."))
        self.state = 'pending'

        # Enviar correo a los usuarios de correos primordiales
        correos_obj = self.env['correos.primordiales'].search([])
        email_list = [correo.email for correo in correos_obj if correo.email]
        if email_list:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            reservation_url = f"{base_url}/web#id={self.id}&model=reserva.sala&view_type=form"
            subject = f"📅 Nueva Reserva de Sala: {self.name}"
            body_html = f"""
                <p>Se ha recibido una nueva reserva.</p>
                <p><strong>Código:</strong> {self.name}</p>
                <p><strong>Sala:</strong> {self.sala_id.name}</p>
                <p><strong>Motivo:</strong> {self.motivo}</p>
                <p><strong>Desde:</strong> {self.fecha_desde}</p>
                <p><strong>Hasta:</strong> {self.fecha_hasta}</p>
                <p>
                    <a href="{reservation_url}" style="
                        display: inline-block;
                        background-color: #1abc9c;
                        color: #ffffff;
                        padding: 10px 20px;
                        text-decoration: none;
                        border-radius: 4px;">
                        Ver Reserva
                    </a>
                </p>
            """
            mail_vals = {
                'subject': subject,
                'body_html': body_html,
                'email_to': ",".join(email_list),
                'auto_delete': True,
            }
            mail = self.env['mail.mail'].create(mail_vals)
            mail.send()

        return True

    def action_approve(self):
        if self.state != 'pending':
            raise ValidationError(_("La reserva debe estar en estado 'Pendiente de Aprobación' para aprobarla."))
        self.state = 'approved'

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        reservation_url = f"{base_url}/web#id={self.id}&model=reserva.sala&view_type=form"

        # Notificación al empleado responsable
        if self.empleado_responsable_id.work_email:
            subject_resp = f"✅ Reserva Aprobada: {self.name}"
            body_resp = f"""
                <p>Su reserva ha sido aprobada.</p>
                <p><strong>Código:</strong> {self.name}</p>
                <p><strong>Sala:</strong> {self.sala_id.name}</p>
                <p><strong>Motivo:</strong> {self.motivo}</p>
                <p><strong>Desde:</strong> {self.fecha_desde}</p>
                <p><strong>Hasta:</strong> {self.fecha_hasta}</p>
                <p>
                    <a href="{reservation_url}" style="
                        display: inline-block;
                        background-color: #3498db;
                        color: #ffffff;
                        padding: 10px 20px;
                        text-decoration: none;
                        border-radius: 4px;">
                        Ver Reserva
                    </a>
                </p>
            """
            mail_vals_resp = {
                'subject': subject_resp,
                'body_html': body_resp,
                'email_to': self.empleado_responsable_id.work_email,
                'auto_delete': True,
            }
            mail_resp = self.env['mail.mail'].create(mail_vals_resp)
            mail_resp.send()

        # Notificación a cada empleado invitado
        for invitado in self.empleados_invitados_ids:
            if invitado.work_email:
                subject_inv = f"🔔 Notificación de Reserva de Sala: {self.name}"
                body_inv = f"""
                    <p>Usted ha sido invitado a la siguiente reserva de sala.</p>
                    <p><strong>Código:</strong> {self.name}</p>
                    <p><strong>Sala:</strong> {self.sala_id.name}</p>
                    <p><strong>Motivo:</strong> {self.motivo}</p>
                    <p><strong>Desde:</strong> {self.fecha_desde}</p>
                    <p><strong>Hasta:</strong> {self.fecha_hasta}</p>
                    <p>
                        <a href="{reservation_url}" style="
                            display: inline-block;
                            background-color: #e67e22;
                            color: #ffffff;
                            padding: 10px 20px;
                            text-decoration: none;
                            border-radius: 4px;">
                            Ver Reserva
                        </a>
                    </p>
                """
                mail_vals_inv = {
                    'subject': subject_inv,
                    'body_html': body_inv,
                    'email_to': invitado.work_email,
                    'auto_delete': True,
                }
                mail_inv = self.env['mail.mail'].create(mail_vals_inv)
                mail_inv.send()

        return True

    def action_reject(self):
        if self.state != 'pending':
            raise ValidationError(_("La reserva debe estar en estado 'Pendiente de Aprobación' para rechazarla."))
        self.state = 'rejected'

        # Notificación al empleado responsable
        if self.empleado_responsable_id.work_email:
            subject = f"❌ Reserva Rechazada: {self.name}"
            body_html = f"""
                <p>Su reserva ha sido rechazada.</p>
                <p><strong>Código:</strong> {self.name}</p>
                <p><strong>Sala:</strong> {self.sala_id.name}</p>
                <p><strong>Motivo:</strong> {self.motivo}</p>
                <p><strong>Desde:</strong> {self.fecha_desde}</p>
                <p><strong>Hasta:</strong> {self.fecha_hasta}</p>
            """
            mail_vals = {
                'subject': subject,
                'body_html': body_html,
                'email_to': self.empleado_responsable_id.work_email,
                'auto_delete': True,
            }
            mail = self.env['mail.mail'].create(mail_vals)
            mail.send()

        return True

    def action_reset_draft(self):
        if self.state != 'rejected':
            raise ValidationError(_("La reserva debe estar en estado 'Rechazada' para restablecer a borrador."))
        self.state = 'draft'
        return True

    @api.constrains('fecha_desde', 'fecha_hasta', 'sala_id')
    def _check_fechas_reserva(self):
        for reserva in self:
            # Validación de 2 días de anticipación para usuarios
            if reserva.empleado_responsable_id.user_id.has_group('reserva_salas.group_usuario_reservas'):
                if reserva.fecha_desde < datetime.now() + timedelta(days=2):
                    raise ValidationError(_("Las reservas deben hacerse con al menos 2 días de anticipación."))

            # Validación de duración máxima de 1 hora por día para usuarios
            if reserva.empleado_responsable_id.user_id.has_group('reserva_salas.group_usuario_reservas'):
                dias_reserva = (reserva.fecha_hasta.date() - reserva.fecha_desde.date()).days
                if dias_reserva > 0:
                    if (reserva.fecha_hasta - reserva.fecha_desde) > timedelta(hours=3):
                        raise ValidationError(_("La duración máxima de una reserva es de 1 hora por día."))
                else:
                    if reserva.fecha_hasta - reserva.fecha_desde > timedelta(hours=1):
                        raise ValidationError(_("La duración máxima de una reserva es de 1 hora por día."))

            # Validación de hasta 3 días seguidos para usuarios
            if reserva.empleado_responsable_id.user_id.has_group('reserva_salas.group_usuario_reservas'):
                if (reserva.fecha_hasta.date() - reserva.fecha_desde.date()).days > 3:
                    raise ValidationError(_("Las reservas no pueden exceder de 3 días seguidos."))

            # Validación de solapamiento de reservas en la misma sala
            reservas_solapadas = self.env['reserva.sala'].search([
                ('id', '!=', reserva.id),
                ('sala_id', '=', reserva.sala_id.id),
                ('state', 'in', ['draft', 'pending', 'approved']),
                ('fecha_desde', '<', reserva.fecha_hasta),
                ('fecha_hasta', '>', reserva.fecha_desde),
            ])

            if reservas_solapadas:
                raise ValidationError(
                    _("La sala ya está reservada en este horario. Por favor, elija otra fecha u hora."))

            # Los administradores no tienen restricciones de tiempo
            if reserva.empleado_responsable_id.user_id.has_group('reserva_salas.group_admin_reservas'):
                continue

    @api.depends('fecha_desde', 'fecha_hasta')
    def _compute_duracion(self):
        for reserva in self:
            if reserva.fecha_desde and reserva.fecha_hasta:
                diferencia = reserva.fecha_hasta - reserva.fecha_desde
                horas = diferencia.seconds // 3600
                minutos = (diferencia.seconds % 3600) // 60
                reserva.duracion = f"{horas:02d}:{minutos:02d} horas"
            else:
                reserva.duracion = "00:00 horas"
