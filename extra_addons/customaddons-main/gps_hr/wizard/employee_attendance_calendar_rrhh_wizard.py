from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
from datetime import datetime, timedelta
import pytz

class EmployeeAttendanceCalendarRRHHWizard(models.TransientModel):
    _name = "employee.attendance.calendar.rrhh.wizard"
    _description = "Wizard para Justificación Directa de RRHH"

    tipo = fields.Selection([
        ("entrada", "Entrada"),
        ("salida", "Salida")
    ], string="Tipo de Marcación", required=True)

    def action_confirmar(self):
	    """Crea marcaciones directas de RRHH reutilizando las funciones estándar de conversión horaria."""
	    active_ids = self.env.context.get("active_ids", [])
	    if not active_ids:
		    raise ValidationError(_("No se han seleccionado registros para justificar."))

	    registros = self.env["employee.attendance.calendar"].browse(active_ids)
	    creados, errores = [], []

	    for rec in registros:
		    try:
			    empleado = rec.empleado_id
			    if not empleado:
				    errores.append(f"⚠️ Registro sin empleado asociado (ID {rec.id})")
				    continue
			    if not rec.fecha:
				    errores.append(f"⚠️ {rec.empleado_nombre} → No tiene fecha definida.")
				    continue

			    # ============================
			    # 1️⃣ Calcular hora y convertir a UTC (usando tus métodos estándar)
			    # ============================
			    try:
				    fecha = rec.fecha
				    hora_local = rec._get_jornada_laboral(empleado, fecha, self.tipo)
				    fecha_utc = rec._convertir_a_utc(fecha, hora_local)
			    except Exception as e:
				    errores.append(f"⚠️ {rec.empleado_nombre} → Error al calcular hora laboral: {str(e)}")
				    continue

			    # ============================
			    # 2️⃣ Verificar si ya existe marcación cercana
			    # ============================
			    existente = self.env["employee.attendance.raw"].sudo().search([
				    ("employee_id", "=", empleado.id),
				    ("date_time", ">=", fecha_utc - timedelta(minutes=5)),
				    ("date_time", "<=", fecha_utc + timedelta(minutes=5)),
			    ], limit=1)

			    if existente:
				    errores.append(
					    f"⚠️ {rec.empleado_nombre} → Ya existe una marcación cercana ({existente.date_time.strftime('%Y-%m-%d %H:%M')})"
				    )
				    continue

			    # ============================
			    # 3️⃣ Crear marcación en UTC
			    # ============================
			    self.env["employee.attendance.raw"].sudo().create({
				    "employee_id": empleado.id,
				    "raw_user_id": empleado.id,
				    "date_time": fecha_utc,
			    })

			    creados.append(f"{rec.empleado_nombre} ({self.tipo} → {fecha_utc.strftime('%Y-%m-%d %H:%M')} UTC)")

		    except Exception as e:
			    errores.append(f"❌ {rec.empleado_nombre}: {str(e)}")

	    # ============================
	    # 4️⃣ Notificación final
	    # ============================
	    mensaje = ""
	    if creados:
		    mensaje += "<b>✅ Marcaciones creadas:</b><br/>" + "<br/>".join(creados)
	    if errores:
		    mensaje += "<br/><b>❌ Errores:</b><br/>" + "<br/>".join(errores)

	    self.env.user.notify_info(
		    message=mensaje or "No se procesó ninguna marcación.",
		    title=_("Resultado Justificación RRHH")
	    )

	    return {"type": "ir.actions.act_window_close"}