from odoo import models, fields, api

class MeetingMeetingReport(models.Model):
    """
    Este modelo hereda de 'meeting.meeting' para añadir campos
    y lógica específica para los reportes de administración.
    """
    _inherit = 'meeting.meeting'

    # Campo numérico para poder sumar las horas en los reportes.
    duration_float = fields.Float(string="Duración (Horas)", compute='_compute_duration_float', store=True)

    @api.depends('duration_hours')
    def _compute_duration_float(self):
        """Calcula la duración en formato numérico (float)."""
        for rec in self:
            rec.duration_float = float(rec.duration_hours or 0.0)