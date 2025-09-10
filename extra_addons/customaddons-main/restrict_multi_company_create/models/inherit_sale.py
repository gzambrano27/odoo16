from odoo import api, fields, models, _
from odoo.exceptions import UserError
import threading

class InheritSaleorder(models.Model):
    _inherit = 'sale.order'

    @api.model_create_multi
    def create(self, vals_list):
        # Verifica las compañías activas del usuario, no del contexto
        user = self.env.user
        active_company_ids = self.env.context.get('allowed_company_ids', [])
        active_company_count = len(active_company_ids)

        # Solo si está en entorno interactivo
        if active_company_count > 1 and not self.env.context.get('intercompany_auto') and not self.env.su:
            raise UserError(_("No puede crear registros con más de una compañía activa seleccionada.(SaleOrder)"))

        return super().create(vals_list)