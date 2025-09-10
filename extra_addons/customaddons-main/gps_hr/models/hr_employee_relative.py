# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models,api


class HrEmployeeRelative(models.Model):
    _inherit = 'hr.employee.relative'

    @api.model
    def _get_selection_gender(self):
        return [
            ('male', 'Masculino'),
            ('female', 'Femenino')
        ]

    gender = fields.Selection(selection=_get_selection_gender, string='Género', groups=None, default="male")
