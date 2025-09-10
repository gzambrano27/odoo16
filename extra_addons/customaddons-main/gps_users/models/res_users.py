# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
import re

class ResUsers(models.Model):
    _inherit="res.users"

    _sql_constraints = [
        ('unique_login_usrs', 'unique(login)', 'El login debe ser único.')
    ]

    @api.constrains('login')
    def _check_unique_login(self):
        for user in self:
            if user.login:
                duplicates = self.search([
                    ('login', '=', user.login),
                    ('id', '!=', user.id)
                ], limit=1)
                if duplicates:
                    raise ValidationError('Ya existe otro usuario con este login: %s' % user.login)

    @api.constrains('login')
    def _check_login_format(self):
        email_regex = r'^[^@]+@[^@]+\.[^@]+$'
        numeric_regex = r'^[0-9]+$'

        for user in self:
            login = user.login or ''
            if not re.match(email_regex, login) and not re.match(numeric_regex, login):
                raise ValidationError(_("El login ingresado no es válido."))

    @api.constrains('groups_id')
    def _check_unique_profile_group(self):
        for user in self:
            profile_groups = user.groups_id.filtered(lambda g: g.is_profile)
            if len(profile_groups) > 1:
                raise ValidationError(
                    "Un usuario no puede tener más de un grupo marcado como perfil (is_profile = True)."
                )

    def user_can_login(self):
        value=super().user_can_login()
        brw_user=self
        value1= brw_user.has_group('gps_users.group_can_login')
        if not value1:#not value or
            raise AccessDenied(_("Acceso denegado. Verifique sus credenciales o contacte al administrador."))

        login = brw_user.login or ''
        email_regex = r'^[^@]+@[^@]+\.[^@]+$'
        numeric_regex = r'^[0-9]+$'
        if not re.match(email_regex, login) and not re.match(numeric_regex, login):
            raise AccessDenied(_("Acceso denegado. Verifique sus credenciales o contacte al administrador."))

        return value

    def __copy_from_to_uid(self,to_uid):
        self.ensure_one()
        if self.id in (1,2):
            raise ValidationError(_("No puedes utilizar esta opcion"))
        from_user=self
        to_user = self.browse(to_uid)
        menu_ids = [(6, 0, [each_menu.id for each_menu in from_user.menu_ids])]
        report_ids = [(6, 0, [each_report.id for each_report in from_user.report_ids])]
        groups_id = [(6, 0, [each_group.id for each_group in from_user.groups_id])]
        to_user.write({"menu_ids": menu_ids,
                       "report_ids": report_ids,
                       "groups_id":groups_id
                       })
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            password = vals.get('password')
            if password:
                self._validate_password_strength(password)
        return super().create(vals_list)

    def write(self, vals):
        password = vals.get('password')
        if password:
            self._validate_password_strength(password)
        return super().write(vals)

    def _validate_password_strength(self, password):
        # Obtener parámetros del sistema
        config = self.env['ir.config_parameter'].sudo()
        validation_enabled = config.get_param('password_check_enabled', '1') == '1'

        if not validation_enabled:
            return  # Salta la validación si está desactivada

        min_letters = int(config.get_param('password_min_letters', 3))
        min_digits = int(config.get_param('password_min_digits', 3))
        min_symbols = int(config.get_param('password_min_symbols', 1))

        # Contar caracteres
        letters = len(re.findall(r'[A-Za-z]', password))
        digits = len(re.findall(r'\d', password))
        symbols = len(re.findall(r'[^A-Za-z0-9]', password))

        if letters < min_letters or digits < min_digits or symbols < min_symbols:
            raise ValidationError(_(
                "La contraseña no cumple los requisitos mínimos: "
                f"{min_letters} letras, {min_digits} dígitos y {min_symbols} símbolos."
            ))