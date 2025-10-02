from odoo import models, fields, api, _


class WizardCancelMeeting(models.TransientModel):
    _name = 'wizard.cancel.meeting'
    _description = 'Asistente para Cancelar Reunión'

    # Campo para almacenar la reunión que se está cancelando
    meeting_id = fields.Many2one('meeting.meeting', string='Reunión', readonly=True)

    # Campo para que el usuario escriba el motivo de la cancelación
    reason = fields.Text(string='Motivo de la cancelación', required=True)

    @api.model
    def default_get(self, fields_list):
        res = super(WizardCancelMeeting, self).default_get(fields_list)
        # Asigna automáticamente el meeting_id desde el contexto
        if self.env.context.get('active_model') == 'meeting.meeting' and self.env.context.get('active_id'):
            res['meeting_id'] = self.env.context['active_id']
        return res

    def action_confirm_cancel(self):
        """
        Esta acción se ejecuta al hacer clic en 'Confirmar'.
        Cancela la reunión y guarda el motivo.
        """
        self.ensure_one()
        if self.meeting_id:
            self.meeting_id.write({
                'state': 'cancelled',
                'cancel_reason': self.reason
            })
        return {'type': 'ir.actions.act_window_close'}