# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _, SUPERUSER_ID
import base64


class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    salary_rule_id=fields.Many2one('hr.salary.rule',"Regla Salarial")
    subsidies_period=fields.Integer("Dias de Subsidio por Periodo",default=0)
    vacations=fields.Boolean("Para vacaciones")