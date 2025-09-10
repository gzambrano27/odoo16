# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.tools.config import config


class HrEmployeeLiquidationAccount(models.Model):
    _name = "hr.employee.liquidation.account"
    _description = "Cuentas de Liquidacion de Empleados"

    company_id = fields.Many2one( related="liquidation_id.company_id",store=False,readonly=True    )
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)
    liquidation_id=fields.Many2one('hr.employee.liquidation','Liquidación de Empleado',ondelete="cascade")
    sequence=fields.Integer("#",default=1,required=True)
    account_id=fields.Many2one("account.account","Cuenta",required=False)
    rule_id = fields.Many2one("hr.salary.rule", "Rubro", required=False)
    debit=fields.Monetary("Débito",default=0.00)
    credit = fields.Monetary("Crédito", default=0.00)
    locked=fields.Boolean('Bloqueado',default=False)
    origin=fields.Selection([('automatic','Automatico'),('manual','Manual')],string="Origen",default="manual")

    @api.constrains('debit', 'credit')
    def _check_positive_amounts(self):
        for record in self:
            if record.debit < 0:
                raise ValidationError(_("El valor en 'Débito' no puede ser menor a 0."))
            if record.credit < 0:
                raise ValidationError(_("El valor en 'Crédito' no puede ser menor a 0."))

    @api.onchange('debit', 'credit')
    def _onchange_debit_credit(self):
        for record in self:
            warnings = []
            if record.debit < 0:
                warnings.append("El valor en 'Débito' no puede ser menor a 0.")
            if record.credit < 0:
                warnings.append("El valor en 'Crédito' no puede ser menor a 0.")
            if warnings:
                return {
                    'warning': {
                        'title': "Advertencia de Validación",
                        'message': '\n'.join(warnings),
                    }
                }

