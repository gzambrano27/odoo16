from odoo import models, fields, api

class MailChannel(models.Model):
    _inherit = 'mail.channel'

    def _subscribe_users_automatically_get_members(self):
        """ Sobrescribir la función para manejar usuarios correctamente """
        result = {}
        for channel in self:
            # Filtrar solo los usuarios válidos con partner_id
            new_members = (channel.group_ids.mapped('users.partner_id') - channel.channel_partner_ids).filtered(lambda p: p.active)
            result[channel.id] = new_members.ids
        return result

    def _subscribe_users_automatically(self):
        new_members = self._subscribe_users_automatically_get_members()
        if new_members:
            to_create = [
                {'channel_id': channel_id, 'partner_id': partner_id}
                for channel_id in new_members
                for partner_id in new_members[channel_id]
            ]
            self.env['mail.channel.member'].sudo().create(to_create)