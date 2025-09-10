# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from ...calendar_days.tools import DateManager
from odoo.exceptions import ValidationError,UserError
dtObj=DateManager()

import re


def normalize_text(text):
    """
    Normaliza un texto:
    - Reemplaza vocales con tilde por vocales sin tilde.
    - Sustituye espacios en blanco por un punto.
    - Remueve cualquier carácter adicional.
    """
    # Diccionario para reemplazar vocales con tilde
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
    }

    # Reemplazar vocales con tilde
    for accented, unaccented in replacements.items():
        text = text.replace(accented, unaccented)

    # Sustituir espacios en blanco por puntos
    text = re.sub(r'\s+', '.', text)

    # Remover caracteres adicionales (solo letras, puntos y números permitidos)
    text = re.sub(r'[^a-zA-Z0-9.]', '', text)

    return text

class HrEmployee(models.Model):
    _inherit="hr.employee"

    @api.model
    def _get_default_lock_biometric(self):
        param_lock_biometric = self.env['ir.config_parameter'].sudo().get_param('lock.biometric.device.id',
                                                                                     "False")
        return param_lock_biometric in ("1", "True")

    lock_biometric = fields.Boolean("Bloquear ID Biométrico", compute="_compute_lock_biometric",
                                        default=_get_default_lock_biometric)
    device_id_num = fields.Char("ID Biométrico", required=True)

    def _compute_lock_biometric(self):
        for brw_each in self:
            lock_biometric = self._get_default_lock_biometric()
            brw_each.lock_biometric = lock_biometric

    def clean_name(self):
        self.ensure_one()
        name=self.name
        return normalize_text(name)