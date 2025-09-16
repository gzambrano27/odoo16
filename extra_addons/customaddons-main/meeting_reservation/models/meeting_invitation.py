from odoo import api, fields, models


class MeetingInvitation(models.Model):
    _name = 'meeting.invitation'
    _description = 'Invitación a reunión'

    meeting_id = fields.Many2one('meeting.meeting', string='Reunión')
    employee_id = fields.Many2one('hr.employee', string='Empleado')
    department = fields.Char(string='Departamento')

    state = fields.Selection([
        ('waiting', 'En espera'),
        ('accepted', 'Aceptada'),
        ('rejected', 'Rechazada'),
    ], default='waiting')

    # Campo técnico para controlar si el usuario logueado es el invitado
    is_my_invitation = fields.Boolean(
        string="Es mi invitación", compute="_compute_is_my_invitation", store=False
    )

    def _compute_is_my_invitation(self):
        for inv in self:
            inv.is_my_invitation = (inv.employee_id.user_id == self.env.user)

    # Al elegir empleado, asignar automáticamente su departamento
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for inv in self:
            inv.department = (
                inv.employee_id.department_id.name
                if inv.employee_id and inv.employee_id.department_id
                else ''
            )

    def action_send_invitation(self):
        for inv in self:
            if inv.employee_id and inv.employee_id.user_id:
                html = f"<p><b>Invitación a la reunión:</b></p>" + inv.meeting_id._get_meeting_details_html()
                inv.meeting_id._send_meeting_mail(
                    inv.employee_id.user_id.partner_id,
                    f"Invitación a reunión: {inv.meeting_id.name}",
                    html
                )
