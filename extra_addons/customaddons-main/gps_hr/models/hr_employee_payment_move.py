# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _

class HrEmployeePaymentMove(models.Model):
    _name = "hr.employee.payment.move"
    _description = "Detalle de Asiento Contable para Pagos"

    process_id = fields.Many2one("hr.employee.payment", "Proceso", ondelete="cascade")
    company_id = fields.Many2one("res.company", string="Compañia", related="process_id.company_id", store=False,
                                 readonly=True)
    currency_id = fields.Many2one("res.currency", "Moneda", related="company_id.currency_id", store=False,
                                  readonly=True)
    account_id = fields.Many2one("account.account", "Cuenta", required=False)
    partner_id = fields.Many2one("res.partner", "Contacto", required=False)

    move_id=fields.Many2one("account.move",string="# Asiento")
    move_line_id = fields.Many2one("account.move.line", string="Linea de Asiento")

    debit = fields.Monetary("Débito",readonly=False, required=False, digits=(16, 2))
    credit = fields.Monetary("Crédito", readonly=False, required=False, digits=(16, 2))

    payslip_id=fields.Many2one('hr.payslip','Rol')
    movement_line_id = fields.Many2one('hr.employee.movement.line', 'Linea de Movimiento')



    _order = "debit desc,credit asc,account_id asc"
    _rec_name = "account_id"