# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.tools.config import config


class HrEmployeeLiquidationLine(models.Model):
    _name = "hr.employee.liquidation.line"
    _description = "Detalle de Liquidacion de Empleados"

    company_id = fields.Many2one( related="liquidation_id.company_id",store=False,readonly=True    )
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)

    liquidation_id=fields.Many2one('hr.employee.liquidation','Liquidacion de Empleados',ondelete="cascade")

    rule_id=fields.Many2one('hr.salary.rule','Rubro',required=True)
    category_id = fields.Many2one('hr.salary.rule.category', 'Categoria', required=True)

    _order = "category_id asc,amount desc"

    category_code = fields.Char(related="category_id.code", store=False, readonly=True)

    name=fields.Char('Descripcion',required=True)
    transaction_type=fields.Selection([('income','Ingresos'),
                                       ('expense','Gastos'),
                                       ('provision','Provision')],string="Tipo",default="income")
    amount=fields.Monetary("Valor",default=0.00)
    amount_original = fields.Monetary("Valor Original", default=0.00)
    sequence=fields.Integer("#",default=1,required=True)

    comments=fields.Text("Comentarios")

    signed_amount = fields.Monetary(
        string="Valor con signo",
        compute='_compute_signed_amount',
        store=True
    )

    type=fields.Selection([('liquidation','Liquidacion'),
                           ('payslip','Rol')],string="Tipo",default="liquidation")

    _order="liquidation_id asc,transaction_type desc,sequence asc"


    @api.constrains('amount', 'amount_original')
    def _check_amounts_positive(self):
        for record in self:
            if record.amount < 0:
                raise ValidationError(_("El campo 'Valor' no puede ser menor a 0."))
            if record.amount_original < 0:
                raise ValidationError(_("El campo 'Valor Original' no puede ser menor a 0."))

    @api.onchange('debit', 'credit')
    def _onchange_debit_credit(self):
        for record in self:
            warning_msgs = []
            if record.debit < 0:
                warning_msgs.append("El valor en 'Débito' no puede ser menor a 0.")
            if record.credit < 0:
                warning_msgs.append("El valor en 'Crédito' no puede ser menor a 0.")
            if warning_msgs:
                return {
                    'warning': {
                        'title': "Advertencia de Validación",
                        'message': '\n'.join(warning_msgs),
                    }
                }


    @api.depends('amount', 'transaction_type')
    @api.onchange('amount', 'transaction_type')
    def _compute_signed_amount(self):
        for record in self:
            if record.transaction_type == 'expense':
                record.signed_amount = -abs(record.amount)
            else:
                record.signed_amount = abs(record.amount)

    @api.onchange('rule_id')
    def onchange_rule_id(self):
        name=None
        if self.rule_id:
            name=self.rule_id.name
        self.name=name






