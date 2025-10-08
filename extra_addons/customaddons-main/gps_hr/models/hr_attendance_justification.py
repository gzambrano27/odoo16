from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, time
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
		("enviado", "Enviado al Jefe Directo"),
		("enviado_rrhh", "Enviado a RRHH"),
		("aprobado", "Aprobado"),
		("rechazado", "Rechazado"),
	], string="Estado", default="borrador", tracking=True)

	jefe_directo_id = fields.Many2one("hr.employee", string="Jefe Directo",
	                                  compute="_compute_jefe_directo", store=True, tracking=True)

	# ========================
	# CÁLCULOS Y CREACIÓN
	# ========================
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

	# ========================
	# ACCIONES
	# ========================
	def action_enviar(self):
		"""Empleado envía solicitud a su jefe directo"""
		for rec in self:
			if rec.empleado_id.user_id.id != self.env.user.id:
				raise ValidationError(_("Solo el empleado dueño de la justificación puede enviarla."))
			if not rec.jefe_directo_id:
				raise ValidationError(_("El empleado no tiene jefe directo configurado."))

			rec.estado = "enviado"

			base_url = rec.get_base_url()
			url = f"{base_url}/web#id={rec.id}&model=hr.attendance.justification&view_type=form"

			if rec.jefe_directo_id.user_id and rec.jefe_directo_id.user_id.partner_id:
				rec.message_post(
					body=_(f"""
                    <div style="border:1px solid #dcdcdc; border-radius:8px; padding:16px; font-family:Arial; background-color:#f9f9f9;">
                        <h3 style="color:#333;">📌 Nueva Solicitud de Justificación</h3>
                        <p><b>Empleado:</b> {rec.empleado_id.name}</p>
                        <p><b>Fecha:</b> {rec.calendario_id.fecha.strftime('%d/%m/%Y') if rec.calendario_id.fecha else ''}</p>
                        <p><b>Tipo:</b> {dict(rec._fields['tipo'].selection).get(rec.tipo, '')}</p>
                        <p><b>Motivo:</b> {rec.motivo_id.nombre}</p>
                        <p><b>Comentario:</b> {rec.comentario or ''}</p>
                        <div style="margin-top:20px;text-align:center;">
                            <a href="{url}" style="display:inline-block;padding:10px 18px;background-color:#017e84;color:#fff;text-decoration:none;border-radius:5px;font-weight:bold;">
                                🔎 Ver Solicitud
                            </a>
                        </div>
                    </div>
                    """),
					subject=_("Nueva Solicitud de Justificación"),
					partner_ids=[rec.jefe_directo_id.user_id.partner_id.id],
					message_type="notification",
					subtype_xmlid="mail.mt_comment",
				)

	def action_enviar_rrhh(self):
		"""Jefe directo o cualquier jefe superior reenvía solicitud a RRHH (departamento id=166)"""
		for rec in self:
			# Buscar el empleado que representa al usuario actual
			empleado_actual = self.env["hr.employee"].sudo().search([("user_id", "=", self.env.user.id)], limit=1)
			if not empleado_actual:
				raise ValidationError(_("Tu usuario no está vinculado a ningún empleado."))

			# Obtener toda la cadena jerárquica de jefes del empleado dueño de la justificación
			jefe = rec.empleado_id.parent_id
			cadena_jefes = self.env["hr.employee"]
			while jefe:
				cadena_jefes |= jefe
				jefe = jefe.parent_id

			# Verificar si el empleado actual está en la cadena de jefes
			if empleado_actual not in cadena_jefes:
				raise ValidationError(_("Solo el jefe directo o un jefe superior puede enviar esta solicitud a RRHH."))

			rec.estado = "enviado_rrhh"

			# Buscar empleados del departamento RRHH (id=166)
			rrhh_empleados = self.env["hr.employee"].sudo().search([("department_id", "=", 166)])
			partners = rrhh_empleados.mapped("user_id.partner_id").ids

			if partners:
				base_url = rec.get_base_url()
				url = f"{base_url}/web#id={rec.id}&model=hr.attendance.justification&view_type=form"

				rec.message_post(
					body=_(f"""
                    <div style="border:1px solid #ccc;border-radius:8px;padding:16px;font-family:Arial;background-color:#f0f9f9;">
                        <h3 style="color:#444;">📩 Solicitud de Justificación enviada a RRHH</h3>
                        <p><b>Empleado:</b> {rec.empleado_id.name}</p>
                        <p><b>Enviada por:</b> {empleado_actual.name}</p>
                        <p><b>Motivo:</b> {rec.motivo_id.nombre}</p>
                        <div style="margin-top:20px;text-align:center;">
                            <a href="{url}" style="display:inline-block;padding:10px 18px;background-color:#0a66c2;color:#fff;text-decoration:none;border-radius:5px;font-weight:bold;">
                                🔎 Revisar Solicitud
                            </a>
                        </div>
                    </div>
                    """),
					subject=_("Solicitud de Justificación enviada a RRHH"),
					partner_ids=partners,
					message_type="notification",
					subtype_xmlid="mail.mt_comment",
				)

	def _get_jornada_laboral(self, empleado, fecha, tipo):
		"""
		Obtiene la hora de entrada o salida según el calendario laboral del empleado.
		Los valores en resource_calendar_attendance están en hora Ecuador (UTC-5),
		por lo que aquí los convertimos a hora UTC del servidor (+5).
		"""
		contrato = empleado.contract_id
		if not contrato or not contrato.resource_calendar_id:
			raise ValidationError(_("El empleado no tiene configurado un calendario de trabajo."))

		calendario = contrato.resource_calendar_id
		dia_semana = str(fecha.weekday())  # lunes = 0, domingo = 6

		# Buscar registros del día
		asistencias = self.env["resource.calendar.attendance"].search([
			("calendar_id", "=", calendario.id),
			("dayofweek", "=", dia_semana),
		])

		if not asistencias:
			raise ValidationError(_("No se encontró una jornada laboral configurada para este día."))

		# ---------------------------
		# 🔹 Determinar hora según tipo
		# ---------------------------
		if tipo == "entrada":
			asistencia = asistencias.filtered(lambda r: r.day_period == "morning")
			if not asistencia:
				raise ValidationError(_(f"No se encontró horario de mañana para el día {fecha}."))
			hora_float = asistencia[0].hour_from
		else:
			asistencia = asistencias.filtered(lambda r: r.day_period == "afternoon")
			if not asistencia:
				raise ValidationError(_(f"No se encontró horario de tarde para el día {fecha}."))
			hora_float = asistencia[0].hour_to

		# ---------------------------
		# 🔹 Convertir float_time → hora local
		# ---------------------------
		hora_int = int(hora_float)
		minutos = int((hora_float - hora_int) * 60)
		hora_local = time(hora_int, minutos)

		# ---------------------------
		# 🔹 Convertir hora Ecuador (UTC-5) → UTC servidor (+0)
		# ---------------------------
		# Combina la fecha con la hora local (Ecuador)
		tz_ecuador = pytz.timezone("America/Guayaquil")
		fecha_local = tz_ecuador.localize(datetime.combine(fecha, hora_local))
		# Convierte a UTC (hora servidor)
		fecha_utc = fecha_local.astimezone(pytz.UTC)

		# Retornar solo la parte de hora en UTC para posterior combinación
		return fecha_utc.time()

	def _convertir_a_utc(self, fecha, hora_local):
		"""
		Combina fecha + hora local (ya ajustada a UTC) y devuelve datetime naive UTC.
		"""
		tz_utc = pytz.UTC
		fecha_utc = tz_utc.localize(datetime.combine(fecha, hora_local))
		return fecha_utc.replace(tzinfo=None)

	def action_aprobar(self):
		"""Aprobación final por RRHH → crea marcación"""
		for rec in self:
			empleado_rrhh = self.env["hr.employee"].sudo().search([("user_id", "=", self.env.user.id)], limit=1)
			if not empleado_rrhh or empleado_rrhh.department_id.id != 166:
				raise ValidationError(_("Solo personal de RRHH puede aprobar definitivamente esta justificación."))

			fecha = rec.calendario_id.fecha
			hora_local = rec._get_jornada_laboral(rec.empleado_id, fecha, rec.tipo)
			dt_utc = rec._convertir_a_utc(fecha, hora_local)

			self.env["employee.attendance.raw"].create({
				"employee_id": rec.empleado_id.id,
				"raw_user_id": rec.empleado_id.id,
				"date_time": dt_utc,
			})
			rec.estado = "aprobado"

	def action_rechazar(self):
		for rec in self:
			rec.estado = "rechazado"

	def action_draft(self):
		for rec in self:
			rec.estado = "borrador"

	# ==================================
	# VISIBILIDAD DE REGISTROS
	# ==================================
	def _get_all_subordinates(self, employee):
		all_subordinates = self.env["hr.employee"]
		to_process = employee.child_ids
		while to_process:
			all_subordinates |= to_process
			to_process = to_process.mapped("child_ids")
		return all_subordinates

	@api.model
	def _where_calc(self, domain, active_test=True):
		domain = domain or []
		if not self._context.get("only_user", False):
			return super(HrAttendanceJustification, self)._where_calc(domain, active_test)

		user = self.env["res.users"].sudo().browse(self._uid)
		if user.has_group("gps_hr.group_empleados_usuarios"):
			employee = self.env["hr.employee"].sudo().search([("user_id", "=", user.id)], limit=1)
			if employee:
				subordinates = self._get_all_subordinates(employee)
				employees_ids = employee.ids + subordinates.ids if subordinates else employee.ids
				domain.append(("empleado_id", "in", employees_ids))
			else:
				domain.append(("empleado_id", "=", -1))
		return super(HrAttendanceJustification, self)._where_calc(domain, active_test)

	def action_batch_aprobar(self):
		"""Aprobación múltiple con detalle de errores"""
		errores = []
		aprobadas = []

		# Verificar si el usuario pertenece a RRHH
		user_employee = self.env["hr.employee"].sudo().search([("user_id", "=", self.env.user.id)], limit=1)
		if not user_employee:
			errores.append("❌ El usuario actual no está vinculado a ningún empleado.")
		else:
			# Verificar si pertenece al departamento RRHH
			rrhh_depto = self.env["hr.department"].sudo().browse(166)
			depto_nombre = rrhh_depto.complete_name or rrhh_depto.name or "RRHH"
			if user_employee.department_id.id != rrhh_depto.id:
				errores.append(f"❌ Solo personal del departamento '{depto_nombre}' puede aprobar justificaciones.")

		if errores:
			raise ValidationError("<br/>".join(errores))

		for rec in self:
			try:
				# Bloquear aprobaciones repetidas o registros rechazados
				if rec.estado == "aprobado":
					errores.append(f"⚠️ {rec.name} → Ya está aprobado, no puede aprobarse nuevamente.")
					continue
				if rec.estado == "rechazado":
					errores.append(f"⚠️ {rec.name} → Está rechazado, no puede aprobarse.")
					continue

				if rec.estado != "enviado_rrhh":
					errores.append(f"⚠️ {rec.name} → Estado inválido: '{rec.estado}'. Debe estar en 'Enviado a RRHH'.")
					continue

				# Validar que tenga calendario y fecha
				if not rec.calendario_id or not rec.calendario_id.fecha:
					errores.append(f"⚠️ {rec.name} → No tiene un calendario o fecha asociada.")
					continue

				fecha = rec.calendario_id.fecha
				hora_local = rec._get_jornada_laboral(rec.empleado_id, fecha, rec.tipo)
				dt_utc = rec._convertir_a_utc(fecha, hora_local)

				# Crear marcación
				self.env["employee.attendance.raw"].sudo().create({
					"employee_id": rec.empleado_id.id,
					"raw_user_id": rec.empleado_id.id,
					"date_time": dt_utc,
				})
				rec.estado = "aprobado"
				aprobadas.append(rec.name)

			except Exception as e:
				errores.append(f"❌ {rec.name} → Error inesperado: {str(e)}")

		# Armar mensaje final
		mensaje = ""
		if aprobadas:
			mensaje += "<b>✅ Justificaciones aprobadas:</b><br/>" + "<br/>".join(aprobadas) + "<br/><br/>"
		if errores:
			mensaje += "<b>❌ Errores encontrados:</b><br/>" + "<br/>".join(errores)

		self.env.user.notify_info(
			message=mensaje or "No se procesó ninguna justificación.",
			title=_("Resultado detallado de aprobación")
		)

	def action_batch_rechazar(self):
		"""Rechazo múltiple con detalle de errores"""
		errores = []
		rechazadas = []

		# Verificar si el usuario pertenece a RRHH
		user_employee = self.env["hr.employee"].sudo().search([("user_id", "=", self.env.user.id)], limit=1)
		if not user_employee:
			errores.append("❌ El usuario actual no está vinculado a ningún empleado.")
		else:
			rrhh_depto = self.env["hr.department"].sudo().browse(166)
			depto_nombre = rrhh_depto.complete_name or rrhh_depto.name or "RRHH"
			if user_employee.department_id.id != rrhh_depto.id:
				errores.append(f"❌ Solo personal del departamento '{depto_nombre}' puede rechazar justificaciones.")

		if errores:
			raise ValidationError("<br/>".join(errores))

		for rec in self:
			try:
				# Bloquear rechazos repetidos o aprobados
				if rec.estado == "rechazado":
					errores.append(f"⚠️ {rec.name} → Ya está rechazado, no puede rechazarse nuevamente.")
					continue
				if rec.estado == "aprobado":
					errores.append(f"⚠️ {rec.name} → Ya está aprobado, no puede rechazarse.")
					continue

				if rec.estado != "enviado_rrhh":
					errores.append(f"⚠️ {rec.name} → Estado inválido: '{rec.estado}'. Debe estar en 'Enviado a RRHH'.")
					continue

				rec.estado = "rechazado"
				rechazadas.append(rec.name)

			except Exception as e:
				errores.append(f"❌ {rec.name} → Error inesperado: {str(e)}")

		# Armar mensaje final
		mensaje = ""
		if rechazadas:
			mensaje += "<b>🚫 Justificaciones rechazadas:</b><br/>" + "<br/>".join(rechazadas) + "<br/><br/>"
		if errores:
			mensaje += "<b>❌ Errores encontrados:</b><br/>" + "<br/>".join(errores)

		self.env.user.notify_info(
			message=mensaje or "No se procesó ninguna justificación.",
			title=_("Resultado detallado de rechazo")
		)
