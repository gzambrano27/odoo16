# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayrollStructureType(models.Model):
    _inherit = 'hr.payroll.structure.type'

    legal_iess=fields.Boolean(string="Afiliado al IESS")
    account = fields.Boolean(string="Realizar Contabilidad", default=True)