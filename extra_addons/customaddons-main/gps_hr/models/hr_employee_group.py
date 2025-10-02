# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import ValidationError

class HrEmployeeGroup(models.Model):
    _name = "hr.employee.group"
    _description = "Grupo de Empleados"

    name = fields.Char(string="Nombre", required=True, index=True)
    active = fields.Boolean(default=True)