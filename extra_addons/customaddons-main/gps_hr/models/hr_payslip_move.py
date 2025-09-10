# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _

class HrPayslipMove(models.Model):
    _name = "hr.payslip.move"
    _description = "Detalle de Asiento Contable con Roles"

    payslip_run_id = fields.Many2one("hr.payslip.run", "Lote de Nomina", ondelete="cascade")
    currency_id = fields.Many2one(related="payslip_run_id.currency_id",store=False,readonly=True)

    payslip_id = fields.Many2one("hr.payslip", "Nomina", ondelete="cascade")
    rule_id = fields.Many2one("hr.salary.rule", "Rubro", required=True)
    account_id = fields.Many2one("account.account", "Cuenta", required=True)
    analytic_account_id=fields.Many2one("account.analytic.account", "Cuenta Analitica", required=False)
    employee_id=fields.Many2one("hr.employee", "Empleado", required=True)
    debit = fields.Monetary("Débito",readonly=False, required=False, digits=(16, 2))
    credit = fields.Monetary("Crédito", readonly=False, required=False, digits=(16, 2))
    abs_total = fields.Monetary("ABS Total",  readonly=False, required=False, digits=(16, 2))

    _order = "debit desc,credit asc,account_id asc"
    _rec_name = "account_id"