# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class HrSalaryRuleAccountAnalytic(models.Model):
    _name = "hr.salary.rule.account.analytic"
    _description = "Cuentas de Rubros para asientos y Cuentas Analiticas"

    rule_account_id=fields.Many2one("hr.salary.rule.account","Rubro",ondelete="cascade")
    department_id = fields.Many2one('hr.department', 'Departamento')
    account_id = fields.Many2one('account.account', 'Cuenta')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Cuenta Analitica')

    @api.constrains('department_id','account_id', 'analytic_account_id')
    def _check_department_or_analytic_account(self):
        for record in self:
            if not record.department_id and (not record.analytic_account_id or not record.account_id):
                raise ValidationError("Debe especificar al menos un Departamento y una Cuenta Analítica o cuenta Contable")