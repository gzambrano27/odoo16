from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HrAttendanceJustificationWizard(models.TransientModel):
    _name = "hr.attendance.justification.wizard"
    _description = "Wizard para Justificación de Asistencia"

    tipo = fields.Selection(
        [("entrada", "Entrada"), ("salida", "Salida")],
        string="Tipo", required=True
    )
    motivo_id = fields.Many2one("hr.attendance.justification.reason", string="Motivo", required=True)
    comentario = fields.Text("Comentario")

    def action_confirmar(self):
	    active_id = self.env.context.get("active_id")
	    if not active_id:
		    raise ValidationError(_("No se encontró la línea de asistencia a justificar."))

	    calendar_line = self.env["employee.attendance.calendar"].browse(active_id)
	    self.env["hr.attendance.justification"].create({
		    "empleado_id": calendar_line.empleado_id.id,
		    "calendario_id": calendar_line.id,
		    "tipo": self.tipo,
		    "motivo_id": self.motivo_id.id,
		    "comentario": self.comentario,
	    })
	    return {"type": "ir.actions.act_window_close"}

