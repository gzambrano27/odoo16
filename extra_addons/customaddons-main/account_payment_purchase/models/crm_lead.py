# models/crm_lead.py
from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Campo para almacenar la secuencia
    opportunity_sequence = fields.Char(string='Opportunity Sequence', readonly=True)

    @api.onchange('stage_id')
    def _onchange_stage_id(self):
        """
        Método que se ejecuta cuando cambia el estado de la oportunidad.
        """
        for record in self:
            # Verifica si el estado es "Ganado"
            if record.stage_id.is_won:
                # Si la secuencia no ha sido asignada aún, se genera una nueva
                if not record.opportunity_sequence:
                    sequence = self.env['ir.sequence'].next_by_code('crm.lead.sequence')
                    record.opportunity_sequence = sequence
