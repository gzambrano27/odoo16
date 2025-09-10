from odoo import api, fields, models, _
from odoo.exceptions import UserError

class InheritReembolso(models.Model):
    _inherit = 'hr.registro.reembolsos'

    @api.model
    def create(self, vals_list):
        if not isinstance(vals_list, list):
            vals_list = [vals_list]

        allowed_companies = self.env.context.get('allowed_company_ids', [])
        if len(allowed_companies) > 1:
            raise UserError(_("No puede crear registros con más de una compañía activa seleccionada."))

        return super().create(vals_list)
