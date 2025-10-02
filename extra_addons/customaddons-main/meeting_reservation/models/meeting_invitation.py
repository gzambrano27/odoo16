from odoo import models, fields, api, _


class MeetingInvitation(models.Model):
    _name = 'meeting.invitation'
    _description = 'Invitación a reunión'

    meeting_id = fields.Many2one('meeting.meeting', string='Reunión', ondelete='cascade')

    personal = fields.Selection([
        ('internal', 'Interno'),
        ('external', 'Externo'),
    ], string="Tipo de persona", default='internal', required=True)

    # Campos para invitados Internos
    employee_id = fields.Many2one('hr.employee', string='Empleado')
    department = fields.Char(string='Departamento', compute='_compute_department', store=True)

    # Campos para invitados Externos
    external_name = fields.Char(string='Nombre')
    external_company = fields.Char(string='Empresa')
    external_reason = fields.Char(string='Motivo')
    external_email = fields.Char(string='Correo')

    # Campos Comunes
    state = fields.Selection([
        ('waiting', 'En espera'),
        ('accepted', 'Aceptada'),
        ('rejected', 'Rechazada'),
    ], default='waiting', string="Estado")

    is_my_invitation = fields.Boolean(
        compute="_compute_is_my_invitation", store=False
    )
    invitation_sent = fields.Boolean(string="Invitación enviada", default=False, readonly=True)

    @api.depends('employee_id.department_id')
    def _compute_department(self):
        for inv in self:
            inv.department = inv.employee_id.department_id.name if inv.employee_id and inv.employee_id.department_id else ''

    def _compute_is_my_invitation(self):
        for inv in self:
            inv.is_my_invitation = (inv.personal == 'internal' and inv.employee_id.user_id == self.env.user)

    def action_send_invitation(self):
        """
        Envía una única invitación (interna o externa) y marca como enviada.
        Esta es la acción final que envía el correo.
        """
        for inv in self:
            partner = self.env['res.partner']
            partner_name = ''

            # Determinar el destinatario (partner)
            if inv.personal == 'internal' and inv.employee_id.user_id.partner_id:
                partner = inv.employee_id.user_id.partner_id
                partner_name = partner.name
            elif inv.personal == 'external' and inv.external_email:
                partner_name = inv.external_name
                # Buscar si ya existe un partner con ese email
                partner = self.env['res.partner'].search([('email', '=', inv.external_email)], limit=1)
                if not partner:
                    partner = self.env['res.partner'].create({
                        'name': inv.external_name,
                        'email': inv.external_email,
                        'company_id': self.env.company.id,
                    })

            # Si encontramos un destinatario válido y hay una reunión asociada...
            if partner and inv.meeting_id:
                # Preparamos y enviamos el correo usando el método centralizado
                subject = _("Invitación a reunión: %s", inv.meeting_id.name)
                body = _("<p>Hola %s,</p><p>Estás invitado a la siguiente reunión:</p>",
                         partner_name) + inv.meeting_id._get_meeting_details_html()

                inv.meeting_id._send_meeting_mail([partner], subject, body)

                # Marcar como enviada
                inv.write({'invitation_sent': True})