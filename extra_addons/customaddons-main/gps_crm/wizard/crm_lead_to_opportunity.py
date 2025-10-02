# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.exceptions import UserError


class Lead2OpportunityPartnerInherit(models.TransientModel):
    _inherit = 'crm.lead2opportunity.partner'

    def action_apply(self):
        # Antes de super, obtengo los leads
        leads = self.env['crm.lead'].browse(self._context.get('active_ids', []))

        # Validación: no permitir convertir si no está revisado
        for lead in leads:
            if not lead.revisado:
                raise UserError(_(
                    "El lead '%s' no puede convertirse en oportunidad porque aún no ha sido revisado o aprobado."
                ) % (lead.name))

        # Ejecutamos la lógica original de Odoo
        action = super(Lead2OpportunityPartnerInherit, self).action_apply()

        # Si hay leads convertidos, notificamos
        if leads:
            self._notify_engineering_group(leads)

        return action

    def _notify_engineering_group(self, opportunities):
        """Envía una notificación al grupo de Ingeniería al convertir en oportunidad"""
        group = self.env.ref('gps_crm.group_crm_engineering_custom', raise_if_not_found=False)
        if not group:
            return

        users = group.users
        if not users:
            return

        message = _(
            "Estimado Usuario, el comité comercial de forma unánime ha dado paso "
            "a la siguiente oportunidad para su conocimiento y pronta gestión."
        )

        # Notificación en el chatter de cada oportunidad convertida
        for opp in opportunities:
            opp.message_post(
                body=message,
                message_type="notification",
                subtype_xmlid="mail.mt_comment",
                partner_ids=users.mapped("partner_id").ids
            )