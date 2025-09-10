from odoo import models, api, _
from odoo.exceptions import UserError

class RestrictMultiCompanyCreate(models.AbstractModel):
    _name = 'restrict.multicompany.mixin'
    _description = 'Bloquea creación si hay más de una empresa activa'

    @api.model
    def create(self, vals_list):
        if not isinstance(vals_list, list):
            vals_list = [vals_list]

        allowed_companies = self.env.context.get('allowed_company_ids', [])

        if len(allowed_companies) > 1:
            raise UserError(_("No se puede crear un registro si tiene más de una compañía activa seleccionada."))

        return super().create(vals_list)
