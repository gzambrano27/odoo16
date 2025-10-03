from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, date, time, timedelta
import pytz

MESES_ES = {
	1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
	5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
	9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE"
}


class HrAttendanceJustification(models.Model):
	_name = 'hr.attendance.justification'
	_description = 'Solicitud de Justificación de Asistencia'
	_inherit = ['mail.thread', 'mail.activity.mixin']

	name = fields.Char("Referencia", tracking=True, readonly=True)

	empleado_id = fields.Many2one("hr.employee", string="Empleado", required=True, readonly=True, tracking=True)
	calendario_id = fields.Many2one("employee.attendance.calendar", string="Registro de Asistencia",
	                                required=True, readonly=True, tracking=True)
	tipo = fields.Selection(
		[("entrada", "Entrada"), ("salida", "Salida")],
		string="Tipo",
		required=True,
		tracking=True
	)
	motivo_id = fields.Many2one("hr.attendance.justification.reason", string="Motivo", required=True, tracking=True)
	comentario = fields.Text("Comentario", tracking=True)
	estado = fields.Selection([
		("borrador", "Borrador"),
		("enviado", "Enviado al Jefe"),
		("aprobado", "Aprobado"),
		("rechazado", "Rechazado"),
	], string="Estado", default="borrador", tracking=True)

	jefe_directo_id = fields.Many2one("hr.employee", string="Jefe Directo",
	                                  compute="_compute_jefe_directo", store=True, tracking=True)

	@api.depends("empleado_id")
	def _compute_jefe_directo(self):
		for rec in self:
			rec.jefe_directo_id = rec.empleado_id.parent_id.id if rec.empleado_id and rec.empleado_id.parent_id else False

	def _formatear_fecha(self, fecha):
		if not fecha:
			return ""
		return f"{fecha.day}/{MESES_ES[fecha.month]}/{fecha.year}"

	@api.model
	def create(self, vals):
		empleado = self.env["hr.employee"].browse(vals.get("empleado_id")) if vals.get("empleado_id") else False
		tipo = dict(self._fields["tipo"].selection).get(vals.get("tipo"), "")
		calendario = self.env["employee.attendance.calendar"].browse(vals.get("calendario_id")) if vals.get(
			"calendario_id") else False

		fecha = calendario.fecha if calendario and calendario.fecha else fields.Date.today()
		fecha_str = self._formatear_fecha(fecha)

		vals["name"] = f"{empleado.name if empleado else ''} - {tipo} - {fecha_str}"
		return super().create(vals)

	def write(self, vals):
		for rec in self:
			empleado = rec.empleado_id if not vals.get("empleado_id") else self.env["hr.employee"].browse(
				vals.get("empleado_id"))
			tipo = dict(self._fields["tipo"].selection).get(vals.get("tipo", rec.tipo), "")
			calendario = rec.calendario_id if not vals.get("calendario_id") else self.env[
				"employee.attendance.calendar"].browse(vals.get("calendario_id"))
			fecha = calendario.fecha if calendario and calendario.fecha else fields.Date.today()
			fecha_str = self._formatear_fecha(fecha)

			vals["name"] = f"{empleado.name if empleado else ''} - {tipo} - {fecha_str}"
		return super().write(vals)

	def action_enviar(self):
		for rec in self:
			if rec.empleado_id.user_id.id != self.env.user.id:
				raise ValidationError(_("Solo el empleado dueño de la justificación puede enviarla."))
			if not rec.jefe_directo_id:
				raise ValidationError(_("El empleado no tiene jefe directo configurado."))

			rec.estado = "enviado"

			# ✅ Construcción de enlace directo al registro
			base_url = rec.get_base_url()
			url = f"{base_url}/web#id={rec.id}&model=hr.attendance.justification&view_type=form"

			# ✅ Notificar al jefe directo por correo con diseño tipo card
			if rec.jefe_directo_id.user_id and rec.jefe_directo_id.user_id.partner_id:
				rec.message_post(
					body=_(f"""
	                <div style="border:1px solid #dcdcdc; border-radius:8px; padding:16px; font-family:Arial, sans-serif; background-color:#f9f9f9;">
	                    <h3 style="color:#333; margin-bottom:12px;">📌 Nueva Solicitud de Justificación de Asistencia</h3>
	                    <p><b>Empleado:</b> {rec.empleado_id.name}</p>
	                    <p><b>Fecha:</b> {rec.calendario_id.fecha.strftime('%d/%m/%Y') if rec.calendario_id.fecha else ''}</p>
	                    <p><b>Tipo:</b> {dict(rec._fields['tipo'].selection).get(rec.tipo, '')}</p>
	                    <p><b>Motivo:</b> {rec.motivo_id.nombre}</p>
	                    <p><b>Comentario:</b> {rec.comentario or ''}</p>
	                    <div style="margin-top:20px; text-align:center;">
	                        <a href="{url}" style="display:inline-block; padding:10px 18px; background-color:#017e84; color:#fff; text-decoration:none; border-radius:5px; font-weight:bold;">
	                            🔎 Ver Solicitud
	                        </a>
	                    </div>
	                </div>
	                """),
					subject=_("Nueva Solicitud de Justificación de Asistencia"),
					partner_ids=[rec.jefe_directo_id.user_id.partner_id.id],
					message_type="notification",
					subtype_xmlid="mail.mt_comment",
				)

	def _get_jornada_laboral(self, empleado, fecha, tipo):
		""" Devuelve la hora de entrada o salida según la jornada del empleado """
		contrato = empleado.contract_id
		if not contrato or not contrato.resource_calendar_id:
			raise ValidationError(_("El empleado no tiene configurado un calendario de trabajo."))

		calendario = contrato.resource_calendar_id

		# día de la semana en formato Odoo (0 = lunes, 6 = domingo)
		dia_semana = str((fecha.weekday()))

		# buscar la asistencia para ese día
		asistencia = self.env["resource.calendar.attendance"].search([
			("calendar_id", "=", calendario.id),
			("dayofweek", "=", dia_semana),
		], order="hour_from ASC", limit=1)

		if not asistencia:
			raise ValidationError(_("No se encontró una jornada laboral configurada para este día."))

		if tipo == "entrada":
			hora_local = time(int(asistencia.hour_from), int((asistencia.hour_from % 1) * 60))
		else:
			hora_local = time(int(asistencia.hour_to), int((asistencia.hour_to % 1) * 60))

		return hora_local

	def _convertir_a_utc(self, fecha, hora_local):
		""" Combina fecha + hora_local en zona America/Guayaquil y lo pasa a naive UTC """
		tz = pytz.timezone("America/Guayaquil")
		dt_local = tz.localize(datetime.combine(fecha, hora_local))
		dt_utc = dt_local.astimezone(pytz.UTC)
		return dt_utc.replace(tzinfo=None)  # ✅ naive datetime en UTC

	def action_aprobar(self):
		for rec in self:
			if rec.jefe_directo_id.user_id.id != self.env.user.id:
				raise ValidationError(_("Solo el jefe directo puede aprobar esta justificación."))

			fecha = rec.calendario_id.fecha
			hora_local = rec._get_jornada_laboral(rec.empleado_id, fecha, rec.tipo)
			dt_utc = rec._convertir_a_utc(fecha, hora_local)

			self.env["employee.attendance.raw"].create({
				"employee_id": rec.empleado_id.id,
				"raw_user_id": rec.empleado_id.id,  # ✅ enviamos también el empleado en raw_user_id
				"date_time": dt_utc,  # UTC naive
			})
			rec.estado = "aprobado"

	def action_rechazar(self):
		for rec in self:
			if rec.jefe_directo_id.user_id.id != self.env.user.id:
				raise ValidationError(_("Solo el jefe directo puede rechazar esta justificación."))
			rec.estado = "rechazado"

	def action_draft(self):
		for rec in self:
			if rec.jefe_directo_id.user_id.id != self.env.user.id:
				raise ValidationError(_("Solo el jefe directo puede regresar a borrador esta justificación."))
			rec.estado = "borrador"

	def _get_all_subordinates(self, employee):
		""" Devuelve todos los subordinados recursivos de un empleado """
		all_subordinates = self.env["hr.employee"]
		to_process = employee.child_ids
		while to_process:
			all_subordinates |= to_process
			to_process = to_process.mapped("child_ids")
		return all_subordinates

	@api.model
	def _where_calc(self, domain, active_test=True):
		""" Restringir las solicitudes visibles según si el empleado tiene personal a cargo """
		domain = domain or []

		if not self._context.get("only_user", False):
			return super(HrAttendanceJustification, self)._where_calc(domain, active_test)

		user = self.env["res.users"].sudo().browse(self._uid)

		if user.has_group("gps_hr.group_empleados_usuarios"):
			employee = self.env["hr.employee"].sudo().search([("user_id", "=", user.id)], limit=1)
			if employee:
				# ✅ incluir al empleado + todos los subordinados (recursivo)
				subordinates = self._get_all_subordinates(employee)
				employees_ids = employee.ids + subordinates.ids
				if not employees_ids:
					employees_ids = [-1]
				domain.append(("empleado_id", "in", employees_ids))
			else:
				domain.append(("empleado_id", "=", -1))

		return super(HrAttendanceJustification, self)._where_calc(domain, active_test)
