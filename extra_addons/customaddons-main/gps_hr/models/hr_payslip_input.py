# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from odoo.exceptions import ValidationError,UserError
from ...calendar_days.tools import CalendarManager,DateManager,MonthManager

dtObj = DateManager()

class HrPayslipInput(models.Model):
    _inherit="hr.payslip.input"

    input_type_id = fields.Many2one('hr.payslip.input.type', string='Tipo', required=False,
                                    domain="['|', ('id', 'in', _allowed_input_type_ids), ('struct_ids', '=', False)]")
    rule_id = fields.Many2one('hr.salary.rule', string='Rubro', required=False)
    category_id = fields.Many2one('hr.salary.rule.category', string='Categoría',required=True)
    category_code = fields.Char(related="category_id.code", store=False, readonly=True)

    code = fields.Char(string="Código")
    movement_id = fields.Many2one("hr.employee.movement.line", "Movimiento", required=False)

    move_line_id = fields.Many2one("account.move.line", "Linea de Asiento",store=True,readonly=False, required=False,compute="_get_compute_move_line_id")

    original_amount = fields.Monetary("Monto Original", digits=(16, 2), required=True)
    original_pending = fields.Monetary("Pendiente Original", digits=(16, 2), required=True)

    amount = fields.Monetary("Monto", digits=(16, 2), required=True)
    add_iess = fields.Boolean("Agregar IESS", default=False)

    movement_ref_id=fields.Char("# Referencia",required=True)
    date_process = fields.Date("Fecha de Vencimiento",  required=True)
    quota = fields.Integer(string="Cuota", default=1, required=True)
    force_payslip=fields.Boolean("Forzar en Rol",default=False)

    currency_id=fields.Many2one(string="Moneda",related="payslip_id.currency_id",store=False,readonly=True)

    liquidation_id=fields.Many2one('hr.employee.liquidation','Liq. de Haberes',ondelete="cascade",required=False)

    new_liquidation_id = fields.Many2one('hr.employee.liquidation', 'Liq. de Haberes', ondelete="cascade", required=False)

    payslip_id = fields.Many2one('hr.payslip', 'Nomina', ondelete="cascade",required=False)

    def unlink(self):
        move_lines = self.env["hr.employee.movement.line"]
        # Mapeo de movement_id de todos los registros
        move_lines += self.mapped('movement_id')
        # Llamar al metodo unlink del superclase
        values = super(HrPayslipInput, self).unlink()
        # Calcular total solo si hay líneas de movimiento
        if move_lines:
            move_lines._compute_total()
        return values

    @api.onchange('rule_id')
    def _onchange_rule_id(self):
        for record in self:
            if record.rule_id:
                record.category_id = record.rule_id.category_id
                record.movement_ref_id=(record.rule_id.name).upper()
            else:
                record.category_id = False
                record.movement_ref_id=None

    @api.onchange('amount','movement_id')
    def onchange_amount(self):
        warning={}
        #print(self.movement_id,self.movement_id._origin)
        if self.movement_id:
            print('1')
            if not self.amount or self.amount<=0:
                self.amount=self.original_pending
                warning={"title":_("Advertencia"),
                         "message":_("El monto aplicado debe ser mayor a 0.00 ,referencia %s") % (self.movement_ref_id or '',)
                         }
            if self.amount>self.original_pending:
                self.amount=self.original_pending
                warning={"title":_("Advertencia"),
                         "message":_("El monto aplicado NO puede ser mayor al valor pendiente original %s ,referencia %s") % (self.original_pending,self.movement_ref_id,)
                         }
            if self.amount<=0:
                warning = {"title": _("Advertencia"),
                           "message": _(
                               "El monto aplicado debe ser mayor a 0.00 .El valor es %s ") % (
                                          self.original_pending,)
                           }
        if warning:
            return {"warning":warning}

    @api.depends('movement_id')
    def _get_compute_move_line_id(self):
        OBJ_MOVE_LINE=self.env["account.move.line"].sudo()
        for brw_each in self:
            move_line_id=False
            if brw_each.movement_id:
                if brw_each.movement_id.account:##linea de asientos
                    brw_move = brw_each.movement_id.process_id.move_id  #
                    lines_srch=OBJ_MOVE_LINE.search([('move_id','=',brw_move.id),
                                                        ('move_id.state','=','posted'),
                                                      ('movement_line_id','=',brw_each.movement_id.id)])
                    if lines_srch:#si esta referenciado de forma individual aplica para descuentos
                        move_line_id=lines_srch and lines_srch[0].id or False
                    else:#referenciado de forma global
                        domain=[('move_id','=',brw_move.id),
                                ('move_id.state','=','posted'),
                                ]
                        if brw_each.movement_id.rule_id.category_id.code=="IN":
                            domain+=[('credit','>',0)]
                        else:
                            domain+=[('debit','>',0)]
                        lines_srch = OBJ_MOVE_LINE.search(domain)
                        if lines_srch:  # si esta referenciado de forma individual aplica para descuentos
                            move_line_id = lines_srch and lines_srch[0].id or False
            brw_each.move_line_id=move_line_id

    _order="category_id asc,rule_id asc,amount asc"
