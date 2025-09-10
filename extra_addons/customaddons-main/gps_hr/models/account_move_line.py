# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError,UserError

class AccountMoveLine(models.Model):
    _inherit="account.move.line"

    movement_line_id=fields.Many2one("hr.employee.movement.line","Linea de Descuento",copy=False)
    movement_payment_id = fields.Many2one("hr.employee.payment.move", "Detalle de Pago",copy=False)
    liquidation_payment_id = fields.Many2one("hr.employee.liquidation.account", "Detalle de Linea de Liq", copy=False)


    rule_id=fields.Many2one("hr.salary.rule","Rubro",copy=False)