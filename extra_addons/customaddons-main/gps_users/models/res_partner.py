# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
from lxml import etree

class ResPartner(models.Model):
    _inherit="res.partner"

    country_id = fields.Many2one(
        'res.country',
        string='Pais',
        default=lambda self: self.env.ref('base.ec')  # código XML ID del país
    )

    # --- helper común ---
    def _can_manage_partner(self):
        """Devuelve True si el usuario puede crear/editar/eliminar partners según:
                - Pertenece a un grupo permitido
                - Trae bypass en contexto
                - La acción viene desde el modelo res.users (edición desde ficha de usuario)
                """
        enable_lock_partner = self.env['ir.config_parameter'].get_param('enable.lock.partner')
        if enable_lock_partner in ("1","True"):
            allowed_groups = [
                'gps_users.group_can_create_partner',
            ]
            has_allowed_group = any(self.env.user.has_group(g) for g in allowed_groups)
            bypass_ctx = self.env.context.get("bypass_partner_restriction", False)
            from_user = self.env.context.get("params", {}).get("model") == "res.users"
            from_employee = self.env.context.get("params", {}).get("model") == "hr.employee"
            from_company = len((self.env["res.company"].sudo().search([('partner_id','=',self.id)])))>=1
            bypass_from_action = self.env.context.get("bypass_from_action", False)
            test= has_allowed_group or bypass_ctx or from_user
            if has_allowed_group and not ( bypass_ctx or from_user or from_employee or from_company):
                if not "bypass_from_action" in self.env.context:
                    test=bypass_from_action
            return test
        return True

    # --- create ---
    @api.model
    def create(self, vals):
        print(self._context)
        if not self._can_manage_partner() :
            raise ValidationError(
                _("No tiene permisos para crear un contacto. "
                  "Solo lo pueden hacer usuarios de ciertos grupos. "
                  "Por favor contacte con el administrador.")
            )
        return super(ResPartner, self).create(vals)
    
    def _called_from_model(self, *models_names):
        """Devuelve True si la petición HTTP viene desde alguno de esos modelos."""
        params = (self.env.context or {}).get('params') or {}
        return params.get('model') in set(models_names)

    # --- write ---
    def write(self, vals):
        print(self._context)
        if not self._can_manage_partner():
            if  self._has_fields_no_validated(vals):
                if self._called_from_model('res.partner'):
                    raise ValidationError(
                        _("No tiene permisos para modificar este contacto. "
                        "Solo lo pueden hacer usuarios de ciertos grupos. "
                        "Por favor contacte con el administrador.")
                    )
        return super(ResPartner, self).write(vals)

    # --- unlink ---
    def unlink(self):
        if not self._can_manage_partner():
            raise ValidationError(
                _("No tiene permisos para eliminar este contacto. "
                  "Solo lo pueden hacer usuarios de ciertos grupos. "
                  "Por favor contacte con el administrador.")
            )
        return super(ResPartner, self).unlink()

    def _has_fields_no_validated(self, vals):
        exempt_fields = {"message_follower_ids", "activity_ids", "message_ids"}
        return bool(set(vals) - exempt_fields)



