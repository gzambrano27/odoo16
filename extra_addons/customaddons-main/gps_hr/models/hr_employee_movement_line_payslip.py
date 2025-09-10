# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.tools.config import config


class HrEmployeeMovementLinePayslip(models.Model):
    _name = "hr.employee.movement.line.payslip"
    _description = "Detalle de Pagos de Nomina"

    movement_line_id = fields.Many2one('hr.employee.movement.line', string='Detalle de Movimiento', ondelete="cascade")
    company_id = fields.Many2one(related="movement_line_id.company_id", store=False, readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)
    salary_rule_id = fields.Many2one('hr.salary.rule', string='Regla Salarial', required=True)
    amount = fields.Monetary(string='Monto', required=True, default=0.00)

    amount_adjust = fields.Monetary(string='Ajuste', required=True, default=0.00)
    amount_adjust_signed = fields.Monetary(
        string='Ajuste con Signo',
        required=True,
        default=0.00,
        compute='_compute_amount_adjust_signed',
        store=True
    )
    comments = fields.Char(string='Comentarios')

    category_id = fields.Many2one(
        related='salary_rule_id.category_id',
        string='Categoría',
        store=True,
        readonly=True
    )

    category_code = fields.Char(
        related='salary_rule_id.category_id.code',
        string='Código de Categoría',
        store=True,
        readonly=True
    )

    action = fields.Selection([
        ('descontar', 'Descontar'),
        ('devolver', 'Devolver'),
    ], string='Acción', required=True, default="devolver")

    payslip_line_id = fields.Many2one('hr.payslip.line', 'Linea de Nomina')

    account_id=fields.Many2one('account.account','Cuenta')
    debit = fields.Monetary('Debe')
    credit = fields.Monetary('Haber')

    @api.constrains('amount_adjust')
    def _check_amount_adjust_non_zero(self):
        for record in self:
            if not record.amount_adjust:
                raise ValidationError("El monto de ajuste debe ser diferente de 0.")

    @api.depends('amount_adjust', 'action')
    def _compute_amount_adjust_signed(self):
        for rec in self:
            if rec.action == 'descontar':
                rec.amount_adjust_signed = -abs(rec.amount_adjust)
            else:  # devolver
                rec.amount_adjust_signed = abs(rec.amount_adjust)

    @api.onchange('amount_adjust', 'action')
    def _onchange_amount_adjust_signed(self):
        for rec in self:
            if rec.action == 'descontar':
                rec.amount_adjust_signed = -abs(rec.amount_adjust)
            else:  # devolver
                rec.amount_adjust_signed = abs(rec.amount_adjust)