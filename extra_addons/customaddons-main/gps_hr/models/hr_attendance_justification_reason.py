from odoo import models, fields, api

class HrAttendanceJustificationReason(models.Model):
    _name = 'hr.attendance.justification.reason'
    _description = 'Motivos de Justificación de Asistencia'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Para habilitar tracking

    name = fields.Char("Motivo", required=True, tracking=True)
    nombre = fields.Char("Motivo (alias)", required=True, tracking=True)
    descripcion = fields.Text("Descripción", tracking=True)
    activo = fields.Boolean("Activo", default=True, tracking=True)

    @api.onchange('nombre')
    def _sync_name_with_nombre(self):
        """Sincroniza campo name con nombre en cada cambio"""
        for rec in self:
            rec.name = rec.nombre

    @api.model
    def create(self, vals):
        if 'nombre' in vals:
            vals['name'] = vals['nombre']
        return super().create(vals)

    def write(self, vals):
        if 'nombre' in vals:
            vals['name'] = vals['nombre']
        return super().write(vals)
