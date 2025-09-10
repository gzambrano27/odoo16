# -*- coding: utf-8 -*-
from datetime import date
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta

# ------------- QR START -------------
import io, base64
import qrcode
class SseLocation(models.Model):
    _name = "sse.location"
    _description = "Ubicaciones SSE"
    _order = "name"

    name = fields.Char(string="Nombre", required=True, translate=True)

    _sql_constraints = [
        ("name_unique", "unique(name)", "Ese nombre de ubicación ya existe."),
    ]

class SseDocument(models.Model):
    _name = "sse.document"
    _description = "Formulario SSE"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    @api.model
    def get_current_employee(self):
        user = self.env["res.users"].sudo().browse(self._uid)
        employee = self.env["hr.employee"]
        # Comprobar si el usuario tiene permisos de grupo 'group_empleados_usuarios'
        if user.has_group("gps_hr.group_empleados_usuarios"):
            # Buscar el empleado relacionado con el usuario
            employee = self.env["hr.employee"].sudo().search([('user_id', '=', user.id)], limit=1)
        return employee

    @api.model
    def _get_default_personnel(self):
        employee = self.get_current_employee()
        return employee and employee.id or False

    @api.model
    def _get_default_manager_id(self):
        employee = self.get_current_employee()
        if employee:
            brw_parent = employee.sudo().parent_id
            return brw_parent and brw_parent.id or False
        return False

    @api.model
    def _get_default_computer_models(self):
        employee = self.get_current_employee()
        print(employee)
        l = [(5,)]
        if employee:
            actas = self.env["sse.document"].sudo().search([('employee_id', '=', employee.id)], limit=1, order="id desc")
            print(actas)
            last_acta = actas
            if last_acta.equipment_line_ids:
                for brw_modelo in last_acta.equipment_line_ids:
                    l.append((0, 0, {
                        "modelo": brw_modelo.modelo,
                        "marca": brw_modelo.marca,
                        "serial_number": brw_modelo.serial_number,
                        "color": brw_modelo.color,
                    }))
        return l

    # --------------------------------------------------
    # Campos principales
    # --------------------------------------------------
    name = fields.Char(string="Secuencia", default="New", copy=False, readonly=True)
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("pending", "Pendiente"),
            ("approved", "Aprobado"),
            ("denied", "Denegado"),
        ],
        default="draft",
        tracking=True,
        string="Estado aprobación",
    )

    # --------------------------------------------------
    # Datos del solicitante
    # --------------------------------------------------
    employee_id = fields.Many2one(
        "hr.employee", string="Solicitante", required=True, tracking=True,default=_get_default_personnel
    )
    company_id = fields.Many2one(
        related="employee_id.company_id", store=True, string="Compañía"
    )
    identificacion = fields.Char(
        related="employee_id.identification_id", store=True, string="Identificación"
    )
    department_id = fields.Many2one(
        related="employee_id.department_id", store=True, string="Departamento"
    )
    job_id = fields.Many2one(related="employee_id.job_id", store=True, string="Cargo")

    # --------------------------------------------------
    # Jefe directo
    # --------------------------------------------------
    manager_id = fields.Many2one("hr.employee", string="Jefe Directo", tracking=True, required=True,default=_get_default_manager_id)
    is_direct_manager = fields.Boolean(
        compute="_compute_is_direct_manager",
        store=False,
    )
    manager_company_id = fields.Many2one(
        related="manager_id.company_id", store=True, string="Compañía"
    )
    manager_job_id = fields.Many2one(
        related="manager_id.job_id", store=True, string="Cargo"
    )

    # --------------------------------------------------
    # Equipos asignados
    # --------------------------------------------------
    equipment_line_ids = fields.One2many(
        "sse.equipment.line", "document_id", string="Equipos asignados",default=_get_default_computer_models
    )

    # --------------------------------------------------
    # Fechas y vigencia
    # --------------------------------------------------
    issue_date = fields.Date(
        string="Fecha emisión",
        default=fields.Date.context_today,
        required=True,
    )
    expiration_date = fields.Date(
        string="Fecha expiración",
        compute="_compute_expiration_date",
        store=True,

    )
    validity_state = fields.Selection(
        [("vigente", "Vigente"), ("vencido", "Vencido")],
        string="Estado",
        compute="_compute_validity_state",
        store=True,
    )
    manager_department_id = fields.Many2one(  # ▼ NUEVO
        related="manager_id.department_id", store=True, string="Departamento"
    )
    location_id = fields.Many2one(
        "sse.location",
        string="Ubicación",
        tracking=True,
        required=True,
    )
    # --------------------------------------------------
    # Secuencia automática
    # --------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("sse.document")
        return super().create(vals_list)

    # --------------------------------------------------
    # Restricción de fecha expedición
    # --------------------------------------------------
    @api.constrains("issue_date", "expiration_date")
    def _check_expiration_within_one_month(self):
        for rec in self:
            if rec.issue_date and rec.expiration_date:
                if rec.expiration_date < rec.issue_date:
                    raise ValidationError(_("La fecha de expiración no puede ser anterior a la fecha de emisión."))
                max_date = rec.issue_date + relativedelta(months=1)
                if rec.expiration_date > max_date:
                    raise ValidationError(
                        _("La fecha de expiración no puede superar un mes desde la fecha de emisión."))


    @api.depends("issue_date")
    def _compute_expiration_date(self):
        for rec in self:
            rec.expiration_date = (
                rec.issue_date + relativedelta(months=1) if rec.issue_date else False
            )

    @api.depends("manager_id")
    def _compute_is_direct_manager(self):
        current_user = self.env.user
        for rec in self:
            rec.is_direct_manager = (
                rec.manager_id.user_id == current_user if rec.manager_id else False
            )
    # --------------------------------------------------
    # Cálculo vigencia
    # --------------------------------------------------
    @api.depends("expiration_date")
    def _compute_validity_state(self):
        today = date.today()
        for record in self:
            if record.expiration_date and record.expiration_date < today:
                record.validity_state = "vencido"
            else:
                record.validity_state = "vigente"

    # --------------------------------------------------
    # Acciones de workflow
    # --------------------------------------------------
    def action_send(self):
        """Borrador  ➜  Pendiente."""
        for rec in self:
            if rec.state != "draft":
                continue
            rec.write({"state": "pending"})
            # correo al jefe directo
            if hasattr(rec, "_notify_manager_pending"):
                rec._notify_manager_pending()

    def _assert_direct_manager(self):
        """Permite aprobar/denegar solo a:
           • Jefe directo (manager_id.user_id)
           • Cualquier usuario del grupo administrador SSE
        """
        is_admin = self.env.user.has_group("sde_document.group_sse_admin")
        for rec in self:
            if not is_admin and rec.manager_id.user_id != self.env.user:
                raise UserError(
                    _("Solo el jefe directo puede aprobar o denegar la solicitud.")
                )

    def print_sse_report(self):
        self.ensure_one()
        action = self.env.ref("sde_document.action_report_sse_document")
        return action.report_action(self)

    def action_approve(self):
        """Solo jefe directo o grupo admin."""
        self._assert_direct_manager()
        for rec in self:
            if rec.state == "pending":
                rec.state = "approved"
                # correo al solicitante con PDF adjunto
                if hasattr(rec, "_notify_result"):
                    rec._notify_result(approved=True)
        return True

    def action_deny(self):
        """Solo jefe directo o grupo admin."""
        self._assert_direct_manager()
        for rec in self:
            if rec.state == "pending":
                rec.state = "denied"
                # correo al solicitante (sin PDF)
                if hasattr(rec, "_notify_result"):
                    rec._notify_result(approved=False)
        return True

    def action_reset_draft(self):
        self.write({"state": "draft"})

    def _qr_payload(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/web#id={self.id}&model=sse.document&view_type=form"

    # (2) Devuelve la imagen PNG en base64 para el reporte
    def _get_qr_image(self):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(self._qr_payload())
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue())

    # ------------------------------------------------------------
    #  Helpers para correos
    # ------------------------------------------------------------
    def _styled_email(self, inner_html, subject):
        """Envuelve el contenido con el estilo corporativo."""
        return f"""
        <html>
          <head><meta charset="utf-8"></head>
          <body style="font-family: Arial, sans-serif;">
            <div style="max-width:600px;margin:20px auto;border:1px solid #ccc;border-radius:5px;background:#F8F9FA;">
              <div style="background:#8B0000;color:#FFF;padding:15px;text-align:center;">
                <h2 style="margin:0;font-size:22px;">{subject}</h2>
              </div>
              <div style="padding:20px;color:#333;line-height:1.6;">
                {inner_html}
              </div>
              <div style="background:#ECECEC;text-align:center;font-size:12px;color:#666;padding:10px;">
                Mensaje automático – Sistema SSE
              </div>
            </div>
          </body>
        </html>
        """

    def _equipment_table_html(self):
        rows = "".join(
            f"<tr><td>{i + 1}</td><td>{l.modelo or ''}</td><td>{l.marca or ''}</td>"
            f"<td>{l.serial_number or ''}</td><td>{l.color or ''}</td></tr>"
            for i, l in enumerate(self.equipment_line_ids)
        ) or "<tr><td colspan='5'>Sin equipos registrados</td></tr>"
        return ("""
            <table border="1" cellpadding="4" cellspacing="0" style="width:100%;border-collapse:collapse;">
              <thead><tr><th>#</th><th>Modelo</th><th>Marca</th><th>N.º Serie</th><th>Color</th></tr></thead>
              <tbody>{rows}</tbody>
            </table>
        """).format(rows=rows)

    # ------------------------------------------------------------
    #  Disparadores de correo
    # ------------------------------------------------------------
    def _notify_manager_pending(self):
        for rec in self:
            if not rec.manager_id or not rec.manager_id.work_email:
                continue
            base = rec.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = f"{base}/web#id={rec.id}&model=sse.document&view_type=form"
            body = rec._styled_email(f"""
                <p>Estimado/a <b>{rec.manager_id.name}</b>,</p>
                <p>{rec.employee_id.name} del departamento {rec.department_id.name}
                   solicita aprobación para la salida de equipos.</p>
                {rec._equipment_table_html()}
                <p style="text-align:center;margin-top:15px;">
                  <a href="{url}" style="background:#1565C0;color:#FFF;padding:10px 18px;
                     text-decoration:none;border-radius:4px;">Ver solicitud</a>
                </p>
            """, "Nueva solicitud de salida de equipos")
            rec.env['mail.mail'].create({
                "subject": f"SSE pendiente – {rec.name}",
                "email_to": rec.manager_id.work_email,
                "body_html": body,
            }).send()

    def _notify_result(self, approved=True):
        """Envía correo al solicitante; sin adjuntar PDF, con botón Ver registro."""
        for rec in self:
            if not rec.employee_id.work_email:
                continue

            # texto y color según resultado
            status_txt = "APROBADA" if approved else "RECHAZADA"
            status_color = "green" if approved else "red"

            # URL al formulario
            base = rec.env["ir.config_parameter"].sudo().get_param("web.base.url")
            url = f"{base}/web#id={rec.id}&model=sse.document&view_type=form"

            # cuerpo HTML
            body = rec._styled_email(f"""
                <p>Hola <b>{rec.employee_id.name}</b>,</p>
                <p>Tu solicitud <b>{rec.name}</b> ha sido
                   <span style="color:{status_color};">{status_txt}</span>.</p>
                <p style="text-align:center;margin-top:15px;">
                  <a href="{url}" style="background:#1565C0;color:#FFF;
                     padding:10px 18px;text-decoration:none;border-radius:4px;">
                     Ver solicitud
                  </a>
                </p>
            """, "Resultado de solicitud SSE")

            rec.env["mail.mail"].sudo().create({
                "subject": f"SSE {rec.name} – {status_txt}",
                "email_to": rec.employee_id.work_email,
                "body_html": body,
            }).send()
