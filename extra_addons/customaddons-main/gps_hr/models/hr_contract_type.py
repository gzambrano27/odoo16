# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrContractType(models.Model):
    _inherit = 'hr.contract.type'

    struct_id=fields.Many2one("hr.payroll.structure","Estructura Salarial")
    legal_iess=fields.Boolean(string="Afiliado al IESS")
    factor=fields.Float('% Factor Dias',default=1.00)