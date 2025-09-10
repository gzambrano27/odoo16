# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    # ─────────────────────────────────────────────
    # CAMPOS
    # ─────────────────────────────────────────────
    approval_state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("pending", "Pendiente"),
            ("approved", "Aprobado"),
            ("rejected", "Rechazado"),
        ],
        default="draft",
        string="Estado de aprobación",
        tracking=True,
    )

    room_id = fields.Many2one("calendar.room", string="Sala")
    color   = fields.Integer(compute="_compute_color", store=True)

    attendee_count = fields.Integer(
        string="N.º asistentes (incluye organizador)",
        compute="_compute_attendee_count",
        store=True,
    )
    start_readonly = fields.Datetime(
        string="Inicio (readonly)",
        compute="_compute_dates_readonly",
        store=True,
    )
    stop_readonly = fields.Datetime(
        string="Fin (readonly)",
        compute="_compute_dates_readonly",
        store=True,
    )

    # -------------------------------------------------
    # Cálculo: reflejar siempre start/stop reales
    # -------------------------------------------------
    @api.depends("start", "stop")
    def _compute_dates_readonly(self):
        for rec in self:
            rec.start_readonly = rec.start
            rec.stop_readonly = rec.stop
    # ─────────────────────────────────────────────
    # CÓMPUTOS
    # ─────────────────────────────────────────────
    @api.depends("approval_state")
    def _compute_color(self):
        for rec in self:
            rec.color = {"draft": 2, "pending": 3, "approved": 10, "rejected": 1}[rec.approval_state]

    @api.depends("partner_ids", "user_id")
    @api.onchange("partner_ids", "user_id")
    def _compute_attendee_count(self):
        for rec in self:
            partners = rec.partner_ids
            rec.attendee_count = len(partners)

    # ─────────────────────────────────────────────
    # ONCHANGE → dominio dinámico
    # ─────────────────────────────────────────────
    @api.onchange("attendee_ids", "user_id","attendee_count")
    def _onchange_capacity_domain(self):
        """
        Cada vez que cambia el nº de asistentes se filtran las salas
        dejando solo las que permiten 'capacidad_maxima >= asistentes'.
        """
        return {
                "domain": {
                    "room_id": [("capacidad_maxima", ">=", self.attendee_count or 0)]
                } }


    # ─────────────────────────────────────────────
    # VALIDACIÓN DE CAPACIDAD
    # ─────────────────────────────────────────────
    @api.constrains("room_id", "attendee_ids", "user_id")
    def _check_capacity(self):
        for rec in self:
            if not rec.room_id:
                continue
            if rec.attendee_count < rec.room_id.capacidad_minima:
                raise ValidationError(
                    _(
                        "El número de asistentes (%(cnt)s) es menor que la capacidad mínima "
                        "de la sala (%(min)s)."
                    )
                    % {"cnt": rec.attendee_count, "min": rec.room_id.capacidad_minima}
                )
            if rec.attendee_count > rec.room_id.capacidad_maxima:
                raise ValidationError(
                    _(
                        "El número de asistentes (%(cnt)s) supera la capacidad máxima "
                        "de la sala (%(max)s)."
                    )
                    % {"cnt": rec.attendee_count, "max": rec.room_id.capacidad_maxima}
                )

    # ─────────────────────────────────────────────
    # DEMÁS CONSTRAINTS
    # solapamiento, límites semanales, etc.
    # ─────────────────────────────────────────────
    @api.constrains("room_id", "start", "stop")
    def _check_room_overlap(self):
        for rec in self:
            if not rec.room_id:
                continue
            overlap = self.search(
                [
                    ("id", "!=", rec.id),
                    ("room_id", "=", rec.room_id.id),
                    ("approval_state", "!=", "rejected"),
                    ("start", "<", rec.stop),
                    ("stop", ">", rec.start),
                ],
                limit=1,
            )
            if overlap:
                raise ValidationError(
                    _("La sala «%s» ya está reservada entre %s y %s.")
                    % (rec.room_id.name, overlap.start, overlap.stop)
                )

    @api.constrains("start", "stop")
    def _check_user_limits(self):
        for rec in self:
            if rec._is_user_manager_or_responsible():
                continue
            midnight = fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if rec.start < midnight + timedelta(days=1):
                raise ValidationError(_("Debes reservar con al menos 1 día de anticipación."))
            if (rec.stop - rec.start).total_seconds() > 3600:
                raise ValidationError(_("La duración máxima permitida es 1 hora."))
            iso_year, iso_week, _ = rec.start.date().isocalendar()
            week_start = datetime.strptime(f"{iso_year}-W{iso_week}-1", "%G-W%V-%u")
            week_end   = week_start + timedelta(days=7)
            count = self.search_count(
                [
                    ("user_id", "=", rec.user_id.id),
                    ("start", ">=", week_start),
                    ("start", "<",  week_end),
                    ("id", "!=", rec.id),
                    ("approval_state", "!=", "rejected"),
                ]
            )
            if count >= 3:
                raise ValidationError(_("Solo puedes hacer 3 reservas por semana."))

    # ─────────────────────────────────────────────
    # CRUD
    # ─────────────────────────────────────────────
    @api.model
    def create(self, vals):
        vals.setdefault("approval_state", "pending")
        event = super().create(vals)
        if event.room_id and event.room_id.responsible_id:
            event._mail_to_responsible()
        return event

    def action_send(self):
        """
        Convierte la reserva de Borrador a Pendiente y
        notifica al responsable de la sala.
        """
        for rec in self.filtered(lambda r: r.approval_state == "draft"):
            rec.approval_state = "pending"
            if rec.room_id and rec.room_id.responsible_id:
                rec._mail_to_responsible()

    # ─────────────────────────────────────────────
    # ACCIONES (approve / reject)
    # ─────────────────────────────────────────────
    def action_approve(self):
        for rec in self:
            if not rec._is_user_manager_or_responsible():
                raise AccessError(_("Solo el Manager o el Responsable puede aprobar."))
            rec.approval_state = "approved"
            rec._mail_to_organizer(approved=True)

    def action_reject(self):
        for rec in self:
            if not rec._is_user_manager_or_responsible():
                raise AccessError(_("Solo el Manager o el Responsable puede rechazar."))
            rec.approval_state = "rejected"
            rec._mail_to_organizer(approved=False)

    # ─────────────────────────────────────────────
    # AUXILIARES (permisos, correo)
    # ─────────────────────────────────────────────
    def _is_user_manager_or_responsible(self):
        self.ensure_one()
        return (
            self.env.user.has_group("calendar_approval.group_calendar_approval_manager")
            or (self.room_id and self.room_id.responsible_id == self.env.user)
        )

    def _get_mail_to(self, partner):
        if partner.email:
            return partner.email
        if getattr(partner, "work_email", False):
            return partner.work_email
        emp = partner.employee_ids[:1]
        return emp.work_email if emp and emp.work_email else False

    # ─────────────────────────────────────────────
    # DISEÑO DE CORREO
    # ─────────────────────────────────────────────
    def _styled_email(self, inner_html):
        base_url  = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        event_url = f"{base_url}/web#id={self.id}&model=calendar.event&view_type=form"
        return f"""
        <html>
          <head>
            <meta charset="utf-8"/>
            <style>
              .container {{
                font-family: Arial, sans-serif; max-width: 600px; margin: 20px auto;
                border: 1px solid #CCC; border-radius: 5px; overflow: hidden; background: #F8F9FA;
              }}
              .header {{ background:#8B0000; color:#FFF; padding:15px; text-align:center; }}
              .header h2 {{ margin:0;font-size:22px; }}
              .body {{ padding:20px;color:#333;line-height:1.6; }}
              .btn {{
                display:inline-block; background:#8B0000; color:#FFF !important;
                padding:10px 15px; text-decoration:none !important; border-radius:4px; margin-top:20px;
              }}
              .footer {{ background:#ECECEC; text-align:center; font-size:12px; color:#666; padding:10px; }}
            </style>
          </head>
          <body>
            <div class="container">
              <div class="header"><h2>Reserva de Salas</h2></div>
              <div class="body">
                {inner_html}
                <p><a href="{event_url}" class="btn">Ver Reserva</a></p>
              </div>
              <div class="footer">Mensaje automático - Reserva de Salas</div>
            </div>
          </body>
        </html>
        """

    def _send_email(self, subject, html_body, email_to):
        email_from = (
            self.env.user.partner_id.email
            or self.env.company.email
            or "noreply@" + (self.env["ir.config_parameter"].sudo().get_param("web.base.url") or "").split("//")[-1]
        )
        mail = self.env["mail.mail"].sudo().create(
            {
                "subject": subject,
                "body_html": html_body,
                "email_to": email_to,
                "email_from": email_from,
                "author_id": self.env.user.partner_id.id,
                "auto_delete": True,
            }
        )
        mail.sudo().send(raise_exception=False)

    # ------------------ Responsable -----------------
    def _mail_to_responsible(self):
        self.ensure_one()
        partner = self.room_id.responsible_id.partner_id
        email_to = self._get_mail_to(partner) if partner else False
        if not email_to:
            return

        subject = _("Nueva reserva pendiente en la sala %s") % self.room_id.name
        inner = _(
            "<p>Estimad@ <strong>{resp}</strong>,</p>"
            "<p>El usuario <strong>{creador}</strong> solicitó la siguiente reserva:</p>"
            "<p><b>Sala:</b> {sala}<br/><b>Inicio:</b> {ini}<br/><b>Fin:</b> {fin}</p>"
        ).format(
            resp=partner.name,
            creador=self.create_uid.name,
            sala=self.room_id.name,
            ini=fields.Datetime.to_string(self.start),
            fin=fields.Datetime.to_string(self.stop),
        )
        self._send_email(subject, self._styled_email(inner), email_to)

    # ------------------ Organizador -----------------
    def _mail_to_organizer(self, approved=True):
        self.ensure_one()
        organizer = self.create_uid.partner_id
        email_to = self._get_mail_to(organizer) if organizer else False
        if not email_to:
            return

        estado = _("Aprobada") if approved else _("Rechazada")
        color  = "#27AE60" if approved else "#C0392B"
        subject = _("Tu reserva ha sido %s") % estado.lower()

        inner = _(
            "<p>Estimad@ <strong>{org}</strong>,</p>"
            "<p>Tu reserva en la sala <strong>{sala}</strong> ha sido "
            "<span style='color:{color};font-weight:bold;'>{estado}</span> "
            "por <strong>{ap}</strong>.</p>"
            "<p><b>Inicio:</b> {ini}<br/><b>Fin:</b> {fin}</p>"
        ).format(
            org=organizer.name,
            sala=self.room_id.name,
            color=color,
            estado=estado,
            ap=self.env.user.name,
            ini=fields.Datetime.to_string(self.start),
            fin=fields.Datetime.to_string(self.stop),
        )
        self._send_email(subject, self._styled_email(inner), email_to)
