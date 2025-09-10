# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit="res.partner"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            is_customer = vals.get('customer_rank', 0) > 0
            is_supplier = vals.get('supplier_rank', 0) > 0

            if is_customer and not self.env.user.has_group("gps_restricciones.group_create_customers"):
                raise UserError(_("No tienes permisos para crear clientes."))

            if is_supplier and not self.env.user.has_group("gps_restricciones.group_create_suppliers"):
                raise UserError(_("No tienes permisos para crear proveedores."))

        return super().create(vals_list)