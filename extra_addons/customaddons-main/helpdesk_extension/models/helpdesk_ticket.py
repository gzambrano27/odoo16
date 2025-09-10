from odoo import models, fields, api, exceptions

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    name = fields.Char(string="Asunto", required=False)

    partner_id = fields.Many2one('res.partner', string="Usuario")
    partner_id = fields.Many2one(
        'res.partner',
        string="Usuario",
        domain=lambda self: self._get_partner_domain(),
    )


    def _get_partner_domain(self):

        current_user_partner_id = self.env.user.partner_id.id
        return ['|', ('id', '=', current_user_partner_id), ('id', '!=', False)]
    def write(self, vals):
        restricted_fields = {'stage_id', 'priority', 'tag_ids'}
        if any(field in vals for field in restricted_fields):

            if not self.env.user.has_group('helpdesk.group_helpdesk_manager'):
                raise exceptions.AccessError(
                    "Solo los administradores pueden modificar Stage, Prioridad, Etiquetas."
                )
        return super(HelpdeskTicket, self).write(vals)

    create_uid = fields.Many2one('res.users', string="Created By", readonly=True)

    @api.model
    def create(self, vals):

        vals['create_uid'] = self.env.user.id
        return super(HelpdeskTicket, self).create(vals)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Asignar automáticamente el partner_id del usuario logueado."""
        if self.env.user:

            self.partner_id = self.env.user.partner_id  # Asignar el partner_id correspondiente

    @api.onchange('team_id')
    def _onchange_team_id(self):
        """Actualizar el dominio de user_id cuando cambia el team_id."""
        self.user_id=self.team_id.member_ids and self.team_id.member_ids[0] or False
        return {'domain': {'user_id': [('id', 'in', self.team_id.member_ids.ids)]} if self.team_id else {}}