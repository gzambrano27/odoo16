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

class HrPayslipEmployees(models.TransientModel):
    _inherit="hr.payslip.employees"

    @api.model
    def _get_default_type_struct_id(self):
        if "active_id" not in self._context:
            return False
        srch=self.env["hr.payslip.run"].sudo().browse(self._context["active_id"])
        return srch and srch[0].type_struct_id.id or False

    @api.model
    def _get_default_legal_iess(self):
        if "active_id" not in self._context:
            return False
        srch = self.env["hr.payslip.run"].sudo().browse(self._context["active_id"])
        return srch and srch[0].type_struct_id.legal_iess or False

    @api.model
    def _get_default_inactive(self):
        if "active_id" not in self._context:
            return True
        srch = self.env["hr.payslip.run"].sudo().browse(self._context["active_id"])
        return srch and srch[0].inactive or False

    @api.model
    def _get_default_date_end(self):
        if "active_id" not in self._context:
            return fields.Date.context_today(self)
        srch = self.env["hr.payslip.run"].sudo().browse(self._context["active_id"])
        return srch and srch[0].date_end or False

    @api.model
    def _get_default_date_start(self):
        if "active_id" not in self._context:
            return fields.Date.context_today(self)
        srch = self.env["hr.payslip.run"].sudo().browse(self._context["active_id"])
        return srch and srch[0].date_start or False

    type_struct_id = fields.Many2one("hr.payroll.structure.type", "Tipo", required=True,
                                     default=_get_default_type_struct_id)

    legal_iess = fields.Boolean(string="Para Afiliados", default=_get_default_legal_iess)
    inactive = fields.Boolean("Inactivos", default=_get_default_inactive)
    date_end = fields.Date(string="Fecha Corte", default=_get_default_date_end)
    date_start = fields.Date(string="Fecha Inicio", default=_get_default_date_start)

    @api.model
    def _get_employees(self):
        return []

    def compute_sheet(self):
        self.ensure_one()
        if self.env.context.get('active_id'):
            brw_payslip_run = self.env["hr.payslip.run"].browse(self.env.context["active_id"])
            brw_each = self
            ####validaciones globales y por empleados###3
            employee_ids=brw_each.with_context(active_test=not brw_each.inactive).employee_ids
            if not employee_ids:
                raise ValidationError(_("Al menos un empleado debe ser seleccionado"))
            self.env["hr.payslip.run"].sudo().validate_global_variables(brw_payslip_run.year)
            #################################################
            values=brw_each.compute_sheet_override()
            if brw_payslip_run.slip_ids:
                for brw_payslip in brw_payslip_run.slip_ids:
                    brw_payslip.onchange_employee_id()
                    brw_payslip.compute_sheet()
                    brw_payslip.validate_payslip()
            brw_payslip_run.state="draft"
            return values
        return True

    def compute_sheet_override(self):
        self.ensure_one()
        if not self.env.context.get('active_id'):
            from_date = fields.Date.to_date(self.env.context.get('default_date_start'))
            end_date = fields.Date.to_date(self.env.context.get('default_date_end'))
            today = fields.date.today()
            first_day = today + relativedelta(day=1)
            last_day = today + relativedelta(day=31)
            if from_date == first_day and end_date == last_day:
                batch_name = from_date.strftime('%B %Y')
            else:
                batch_name = _('From %s to %s', format_date(self.env, from_date), format_date(self.env, end_date))
            payslip_run = self.env['hr.payslip.run'].create({
                'name': batch_name,
                'date_start': from_date,
                'date_end': end_date,
            })
        else:
            payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))

        employees = self.with_context(active_test=False).employee_ids
        if not employees:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))

        #Prevent a payslip_run from having multiple payslips for the same employee
        employees -= payslip_run.slip_ids.employee_id
        success_result = {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.run',
            'views': [[False, 'form']],
            'res_id': payslip_run.id,
        }
        if not employees:
            return success_result

        payslips = self.env['hr.payslip']
        Payslip = self.env['hr.payslip']
        state='open'
        active=not self.inactive
        domain_contract = []
        if not active:
            state='close'
            filter_date_process=self._context.get("filter_date_process", False)
            filter_date_start=self._context.get("filter_date_start", False)
            if filter_date_process:
                domain_contract += [('date_end', '<=', filter_date_process)]
            if filter_date_start:
                domain_contract += [('date_end', '>=',filter_date_start )]
            domain_contract+=[('state','=',state)]
            domain_contract += [('employee_id', 'in', employees.ids)]
            print(domain_contract)
            contracts=self.env["hr.contract"].sudo().search(domain_contract)
            print(contracts)
        else:
            contracts = (employees._get_contracts(
                payslip_run.date_start, payslip_run.date_end, states=[state, ]
            ))
        if active:
            contracts=contracts.filtered(lambda c: active)
        contracts=contracts.filtered(lambda  x: x.company_id==payslip_run.company_id)
        contracts._generate_work_entries(payslip_run.date_start, payslip_run.date_end)
        default_values = Payslip.default_get(Payslip.fields_get())
        payslips_vals = []
        for contract in self._filter_contracts(contracts):
            values = dict(default_values, **{
                'name': _('New Payslip'),
                'employee_id': contract.employee_id.id,
                'payslip_run_id': payslip_run.id,
                'date_from': payslip_run.date_start,
                'date_to': payslip_run.date_end,
                'contract_id': contract.id,
                'struct_id': self.structure_id.id or contract.structure_type_id.default_struct_id.id,
            })
            payslips_vals.append(values)
        payslips = Payslip.with_context(tracking_disable=True).create(payslips_vals)
        payslips._compute_name()
        payslips.compute_sheet()
        payslip_run.state = 'draft'

        return success_result



