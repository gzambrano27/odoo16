# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from odoo.exceptions import ValidationError,UserError
from ...calendar_days.tools import CalendarManager,DateManager,MonthManager

dtObj = DateManager()

class HrPayslipLine(models.Model):
    _inherit="hr.payslip.line"

    _order="category_id asc,amount desc"

    category_code=fields.Char(related="category_id.code",store=False,readonly=True)

    abs_total = fields.Monetary("ABS Total",store=True,digits=(16,2), compute="_compute_abs_total")

    historic_line_id=fields.Many2one("hr.employee.historic.lines","Historico de Empleado")

    adjust_movement_line_ids=fields.One2many('hr.employee.movement.line.payslip','payslip_line_id','Ajuste')

    adjust_total=fields.Monetary("Valor Ajustado Adicional",store=True,digits=(16,2), compute="_compute_adjust_total")
    pending_adjust_total = fields.Monetary("Valor Pendiente por Ajustar", store=True, digits=(16, 2),
                                   compute="_compute_adjust_total")

    enable_adjust= fields.Boolean("Permite Ajustar", store=True, default=True,
                                   compute="_compute_adjust_total")
    @api.depends('adjust_movement_line_ids')
    def _compute_adjust_total(self):
        DEC=2
        for brw_each in self:
            line_ids=brw_each.adjust_movement_line_ids.filtered(lambda x: x.movement_line_id.process_id.state in ('approved','paid') )
            adjust_total= round(sum(line_ids.mapped('amount_adjust_signed')), DEC)
            pending_adjust_total=0.00
            enable_adjust=(brw_each.category_code in ('OUT','IN'))
            if brw_each.category_code=='OUT':
                pending_adjust_total=brw_each.amount+adjust_total
                enable_adjust=(pending_adjust_total<0.00)
            brw_each.adjust_total =round(adjust_total, DEC)
            brw_each.pending_adjust_total = round(pending_adjust_total,DEC)
            brw_each.enable_adjust=enable_adjust

    @api.onchange('total')
    @api.depends('total')
    def _compute_abs_total(self):
        DEC=2
        for brw_each in self:
            brw_each.abs_total=round(abs(brw_each.total or 0.00),DEC)

    def create_historic_line(self):
        OBJ_HISTORIC=self.env["hr.employee.historic.lines"]
        for brw_each in self:
            vals={
                    "payslip_line_id":brw_each.id,
                    "payslip_id": brw_each.slip_id.id,
                    "employee_id": brw_each.slip_id.employee_id.id,
                    "company_id":brw_each.slip_id.company_id.id,
                    "grouped":False,
                    "month_id":brw_each.slip_id.payslip_run_id.month_id.id,
                    "year": brw_each.slip_id.payslip_run_id.year,
                    "amount":brw_each.abs_total,
                    "rule_id":brw_each.salary_rule_id.id,
                    "state":"draft"
            }
            if not brw_each.historic_line_id:
                brw_historic_line=OBJ_HISTORIC.create(vals)
                brw_each.historic_line_id=brw_historic_line.id
            else:
                brw_each.historic_line_id.write(vals)
        return True

    def action_historic_posted(self):
        for brw_each in self:
            brw_historic_line=brw_each.historic_line_id
            if brw_historic_line:
                brw_historic_line.action_posted()
        return True

    def action_historic_draft(self):
        for brw_each in self:
            brw_historic_line = brw_each.historic_line_id
            if brw_historic_line:
                brw_historic_line.action_draft()
        return True

    def unlink_history(self):
        for brw_each in self:
            brw_historic_line = brw_each.historic_line_id
            if brw_historic_line:
                brw_historic_line.unlink()
        return True