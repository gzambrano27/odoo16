# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_

from collections import defaultdict
from datetime import datetime, date, time
from dateutil.relativedelta import relativedelta

import pytz

from odoo.tools import format_date

from odoo.exceptions import ValidationError,UserError
from ...calendar_days.tools import CalendarManager,DateManager
from ...message_dialog.tools import FileManager
dtObj=DateManager()
clObj=CalendarManager()
flObj=FileManager()

from odoo import models, fields, api

class HrPayslipPaymentWizard(models.TransientModel):
    _name = "hr.payslip.payment.wizard"

    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Rol',
        required=True,
        default=lambda self: self.env.context.get('active_id')
    )
    company_id=fields.Many2one(related="payslip_id.company_id",store=False,readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)
    # Selección manual de líneas del payslip
    payslip_line_ids = fields.Many2many(
        'hr.payslip.line',
        string='Líneas de Rol',
        domain="[('slip_id', '=', payslip_id)]"
    )

    line_ids = fields.One2many(
        'hr.payslip.payment.line.wizard',
        'wizard',
        string='Líneas Generadas'
    )

    total =fields.Monetary(compute="_compute_total",store=True,string="Total",readonly=True)

    comments=fields.Text("Comentarios",default=None,required=True)

    @api.onchange('line_ids','line_ids.amount_adjust_signed')
    @api.depends('line_ids','line_ids.amount_adjust_signed')
    def _compute_total(self):
        DEC=2
        for brw_each in self:
            total=0.00
            for brw_line in brw_each.line_ids:
                total+=brw_line.amount_adjust_signed
            brw_each.total=round(total,DEC)

    @api.onchange('payslip_line_ids')
    def _onchange_payslip_line_ids(self):
        """Crear líneas del wizard cuando se seleccionan líneas del rol"""
        self.line_ids = [(5, 0, 0)]  # borrar anteriores
        for line in self.payslip_line_ids:
            vals = self.env["hr.payslip.payment.line.wizard"].set_values_account(line.salary_rule_id,
                                           self.company_id,0.01)
            vals.update({
                'salary_rule_id': line.salary_rule_id.id,
                'amount': line.total,
                'amount_adjust': 0.01,
                'comments': line.name,
                'action':'devolver',
                'payslip_line_id':line.id,
            })
            self.line_ids += self.line_ids.new(vals)

    def action_confirm_payment(self):
        DEC=2
        brw_rule = self.env.ref('gps_hr.rule_DEVOLUCIONES')

        self.ensure_one()

        not_confirmed = self.payslip_id.filtered(lambda r: r.state != 'paid')
        if not_confirmed:
            raise ValidationError("Todos los registros deben estar en estado 'Pagado' para continuar.")

        if self.total<=0:
            raise ValidationError(_("El total a pagar debe ser mayor a 0.00"))
        payslip_line_ids=[(5,)]
        name=[]
        for brw_line in self.line_ids:
            if brw_line.payslip_line_id:
                if brw_line.payslip_line_id.category_code=='OUT':
                    diff=round(brw_line.payslip_line_id.pending_adjust_total+ brw_line.amount_adjust,DEC)
                    if diff>0.00:
                        raise ValidationError(_("Si es un descuento no puedes devolver un valor mayor al descontado"))
            payslip_line_ids.append((0,0,{
                "salary_rule_id":brw_line.salary_rule_id.id,
                "amount":brw_line.amount,
                "amount_adjust": brw_line.amount_adjust,
                "comments": brw_line.comments,
                "payslip_line_id": brw_line.payslip_line_id and brw_line.payslip_line_id.id or False,
                'account_id':brw_line.account_id and brw_line.account_id.id or False,
                'debit':brw_line.debit,
                'credit': brw_line.credit
            }))
            name.append( brw_line.comments)
        name=",".join(name)
        OBJ_MOVEMENT = self.env["hr.employee.movement"].sudo()

        brw_movement = OBJ_MOVEMENT.create({
            "company_id": self.payslip_id.company_id.id,
            'filter_iess': True,
            'rule_id': brw_rule.id,
            "category_code": brw_rule.category_id.code,
            "category_id": brw_rule.category_id.id,
            "name": "/",
            "date_process": fields.Date.context_today(self),
            "type": "batch",
            "origin": "system"
        })
        brw_movement.onchange_rule_employee_id()
        brw_movement.update_date_info()
        line_ids = [
            (5,),
            (0, 0, {
                "company_id": brw_movement.company_id.id,
                "rule_id": brw_movement.rule_id.id,
                "category_code": brw_movement.category_code,
                "date_process": brw_movement.date_process,
                "year": brw_movement.year,
                "month_id": brw_movement.month_id.id,
                "employee_id":  self.payslip_id.employee_id.id,
                "contract_id":  self.payslip_id.contract_id.id,
                "name": name,
                "comments": self.comments or _("POR DEVOLUCION EN ROL"),
                "department_id":  self.payslip_id.contract_id.department_id.id,
                "job_id":  self.payslip_id.contract_id.job_id.id,
                "bank_account_id":  self.payslip_id.employee_id.bank_account_id and
                                    self.payslip_id.employee_id.bank_account_id.id or False,
                "origin": "compute",
                "total": self.total,
                "total_historic": self.total,
                "quota": 1,
                "type": brw_movement.type,
                "payslip_line_ids":payslip_line_ids,
                'adjust_payslip_id':self.payslip_id.id,
            })
        ]
        brw_movement.write({"line_ids": line_ids,
                            'comments':self.comments  or _("POR DEVOLUCION EN ROL")})
        brw_movement.action_approved()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lotes de Ingresos',
            'res_model': 'hr.employee.movement',
            'view_mode': 'form,tree',
            'domain': [('id', '=', brw_movement.id), ('category_code', '=', 'IN'),
                       ('type', 'in', ('batch', 'batch_automatic'))],
            'context': {'search_default_is_draft':1,'search_default_is_approved':1,'search_default_is_paid':1,'default_type':'batch','default_category_code':'IN'},

            'views': [
               (self.env.ref('gps_hr.hr_employee_movement_view_form').id, 'form'),
                (self.env.ref('gps_hr.hr_employee_movement_view_tree').id, 'tree')
            ],
            'res_id':brw_movement.id,
        }

class HrPayslipPaymentLineWizard(models.TransientModel):
    _name = "hr.payslip.payment.line.wizard"

    wizard = fields.Many2one('hr.payslip.payment.wizard', string='Asistente', ondelete="cascade")
    company_id = fields.Many2one(related="wizard.company_id", store=False, readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)
    salary_rule_id = fields.Many2one('hr.salary.rule', string='Regla Salarial', required=True)
    amount = fields.Monetary(string='Monto',required=True,default=0.00)

    amount_adjust = fields.Monetary(string='Ajuste',required=True,default=0.00)
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
    ], string='Acción', required=True,default="devolver")

    payslip_line_id=fields.Many2one('hr.payslip.line','Linea de Nomina')

    account_id = fields.Many2one('account.account', 'Cuenta')
    debit = fields.Monetary('Debe')
    credit = fields.Monetary('Haber')

    adjust_total = fields.Monetary(related="payslip_line_id.adjust_total")
    pending_adjust_total = fields.Monetary(related="payslip_line_id.pending_adjust_total")

    @api.constrains('amount_adjust')
    def _check_amount_adjust_non_zero(self):
        for record in self:
            if not record.amount_adjust:
                raise ValidationError("El monto de ajuste debe ser diferente de 0.")
            if record.amount_adjust<=0.00:
                raise ValidationError("El monto de ajuste debe ser mayor a 0.")

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

    def set_values_account(self,salary_rule_id,company_id,amount):
        debit,credit=amount,0.00
        srch_account = self.env["hr.salary.rule.account"].sudo().search([
            ('rule_id', '=', salary_rule_id.id),
            ('company_id', '=', company_id.id),
            ('type', '=', 'payslip'),
            ('account_type', '=', 'debit')
        ])
        if salary_rule_id.category_id.code != 'IN':
            srch_account = self.env["hr.salary.rule.account"].sudo().search([
                ('rule_id', '=', salary_rule_id.id),
                ('company_id', '=',company_id.id),
                ('type', '=', 'payslip'),
                ('account_type', '=', 'credit')
            ])
        vals={
            "account_id":srch_account and srch_account.account_id.id or False,
            "debit":debit,
            "credit":credit
        }
        return vals


    @api.onchange('salary_rule_id','payslip_line_id','action','amount_adjust','amount_adjust_signed')
    def onchange_salary_rule_id(self):
        if self.salary_rule_id:
            vals=self.set_values_account(self.salary_rule_id,
                                         self.company_id,self.amount_adjust)
            self.account_id =vals.get('account_id',False)
            self.debit = vals.get('debit',0.00)
            self.credit = vals.get('credit',0.00)
        else:
            self.account_id =False
            self.debit = 0
            self.credit = 0