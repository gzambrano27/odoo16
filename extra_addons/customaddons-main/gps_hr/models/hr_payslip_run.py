# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

from ...calendar_days.tools import CalendarManager, DateManager, MonthManager

dtObj = DateManager()
caObj = CalendarManager()


class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    @api.model
    def get_default_year(self):
        today = fields.Date.context_today(self)
        return today.year

    @api.model
    def get_default_month_id(self):
        today = fields.Date.context_today(self)
        srch = self.env["calendar.month"].sudo().search([('value', '=', today.month)])
        return srch and srch[0].id or False

    @api.model
    def _get_default_company_id(self):
        if self._context.get("allowed_company_ids", []):
            return self._context.get("allowed_company_ids", [])[0]
        return False

    @api.model
    def _get_default_type_struct_id(self):
        srch = self.env["hr.payroll.structure.type"].sudo().search([])
        return srch and srch[0].id or False

    company_id = fields.Many2one("res.company", "Compañía", required=True,default=lambda self: self.env.company,)
    currency_id = fields.Many2one(string="Moneda", related="company_id.currency_id", store=False, readonly=True)

    month_id = fields.Many2one("calendar.month", "Mes", required=True, default=get_default_month_id)
    year = fields.Integer("Año", required=True, default=get_default_year)

    total_in = fields.Monetary("Ingresos", digits=(16, 2), required=False, default=0.00, store=True,
                               compute="_compute_total")
    total_out = fields.Monetary("Egresos", digits=(16, 2), required=False, default=0.00, store=True,
                                compute="_compute_total")
    total_provision = fields.Monetary("Provisión", digits=(16, 2), required=False, default=0.00, store=True,
                                      compute="_compute_total")
    total = fields.Monetary("Total", digits=(16, 2), required=False, default=0.00, store=True, compute="_compute_total")

    type_struct_id = fields.Many2one("hr.payroll.structure.type", "Tipo", required=True,
                                     default=_get_default_type_struct_id)

    legal_iess = fields.Boolean(string="Para Afiliados", default=True, readonly=True, related="type_struct_id.legal_iess")

    move_line_ids = fields.One2many("hr.payslip.move", "payslip_run_id", "Detalle de Asiento")

    date_process = fields.Date(string="Fecha de Proceso", required=False, help="Fecha de Contabilización del Rol")

    start_job_mail = fields.Boolean("Enviar por correo", default=False)
    end_job_mail = fields.Boolean("Finalizado envio de correo", default=False)

    _check_company_auto = True

    has_payment = fields.Boolean(compute="_compute_residual_payment", string="Tiene Pago Pendiente",
                                 store=True, readonly=True, default=False)

    inactive=fields.Boolean("Inactivo",default=False)

    @api.depends('slip_ids', 'slip_ids.has_payment')
    def _compute_residual_payment(self):
        for brw_each in self:
            has_payment = True
            for brw_line in brw_each.slip_ids:
                if not brw_line.has_payment:
                    has_payment = False
                    continue
            brw_each.has_payment = has_payment

    @api.depends('slip_ids', 'state')
    def _compute_state_change(self):
        pass

    @api.onchange('company_id', 'month_id', 'year', 'type_struct_id')
    def onchange_company_dates(self):
        name = None
        if self.company_id and self.month_id and self.year:
            name = "NOMINA %s DE %s DEL %s PARA %s(%s)" % (
                self.type_struct_id.name,
                self.month_id.name, self.year, self.company_id.name,
                self.type_struct_id and self.type_struct_id.name or '')
            name = name.upper()
        self.name = name
        self.slip_ids = [(5,)]

    @api.onchange('month_id', 'year')
    def onchange_year_month_id(self):
        if self.month_id and self.year:
            self.date_start = dtObj.create(self.year, self.month_id.value, 1)
            self.date_end = dtObj.create(self.year, self.month_id.value, caObj.days(self.year, self.month_id.value))
        else:
            self.date_start = None
            self.date_end = None
        self.date_process = self.date_end
        self.slip_ids = [(5,)]

    @api.onchange('slip_ids', 'slip_ids.total_in', 'slip_ids.total_out', 'slip_ids.total_provision',
                  'slip_ids.total_payslip')
    def onchange_line_ids(self):
        self._origin.update_total()

    @api.depends('slip_ids', 'slip_ids.total_in', 'slip_ids.total_out', 'slip_ids.total_provision',
                 'slip_ids.total_payslip')
    def _compute_total(self):
        for brw_each in self:
            brw_each.update_total()

    def update_total(self):
        DEC = 2
        for brw_each in self:
            total_in, total_out, total_provision, total = 0.00, 0.00, 0.00, 0.00
            for brw_line in brw_each.slip_ids:
                total_in += brw_line.total_in
                total_out += brw_line.total_out
                total_provision += brw_line.total_provision
                total += brw_line.total_payslip
            brw_each.total_in = round(total_in, DEC)
            brw_each.total_out = round(total_out, DEC)
            brw_each.total_provision = round(total_provision, DEC)
            brw_each.total = round(total, DEC)

    _order = "id desc"

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        raise ValidationError(_("No puedes duplicar este documento"))

    def unlink(self):
        move_lines = self.env["hr.employee.movement.line"]
        # Filtrar los registros que no están en estado 'draft' al inicio
        if any(brw_each.state != 'draft' for brw_each in self):
            raise ValidationError(_("No puedes borrar un registro que no sea preliminar"))
        # Mapeo de las líneas de entrada en una sola operación
        inputs = self.mapped('slip_ids.input_line_ids')
        if inputs:
            move_lines += inputs.mapped('movement_id')
        # Llamar al metodo unlink del superclase
        values = super(HrPayslipRun, self).unlink()
        # Calcular total solo si hay líneas de movimiento
        if move_lines:
            move_lines._compute_total()
        return values

    def compute_sheets(self):
        for brw_each in self:
            if brw_each.state != "draft":
                raise ValidationError(_("Solo puedes calcular un rol en estado 'preliminar' "))
            if brw_each.slip_ids:
                for brw_slip in brw_each.slip_ids:
                    brw_slip.compute_sheet()

        return True

    @api.model
    def validate_global_variables(self, year):
        srch = self.env["th.legal.wages"].sudo().search([('name', '=', year), ('state', '=', True)])
        if not srch:
            raise ValidationError(_("Debes definir un salario basico para el año %s") % (year,))

    def validate_payslips(self):
        for brw_each in self:
            if brw_each.slip_ids:
                for brw_slip in brw_each.slip_ids:
                    brw_slip.validate_payslip()
        return True

    def action_verify(self):
        for brw_each in self:
            brw_each.validate_slips()
            brw_each.validate_partner_accounts()
            for brw_payslip in brw_each.slip_ids:
                brw_payslip.action_verify()
            brw_each.write({"state": "verify"})
            brw_each.calculate_moves()
        return True

    def validate_partner_accounts(self):
        brw_each=self
        afiliado = brw_each.type_struct_id.legal_iess
        lines=self.env['hr.payslip']
        for brw_line in brw_each.slip_ids:
            if not afiliado:
                partner_ids =  brw_line.employee_id.partner_id
                if  brw_line.employee_id.tiene_ruc:
                    partner_ids =  brw_line.employee_id.ruc_partner_id
                if not partner_ids:
                    lines+= brw_line
        if lines:
            employees_names='\n,'.join(lines.mapped('employee_id.name'))
            raise ValidationError(_("No hay contatos definidos para contabilizar para:  %s") % (employees_names,))
        return True

    def action_draft(self):
        for brw_each in self:
            brw_each.action_reverse_payment_request()
            vals={"move_line_ids": [(5,)]}
            if brw_each.move_id:
                if brw_each.move_id.state != 'cancel':
                    brw_each.move_id.button_draft()
                    brw_each.move_id.button_cancel()
                if brw_each.move_id.state != 'cancel':
                    raise ValidationError(_("El documento contable %s debe estar anulado") % (brw_each.move_id.name,))
                vals["move_id"]=False
            brw_each.write(vals)
            for brw_payslip in brw_each.slip_ids:
                brw_payslip.remove_lines_historic()
        values=super(HrPayslipRun, self).action_draft()
        for brw_each in self:
            for brw_payslip in brw_each.slip_ids:
                brw_payslip.remove_lines_historic()
        return values

    def restore_movements(self):
        for brw_each in self:
            if brw_each.state != 'draft':
                raise ValidationError(_("Esta acción solo puede ser ejecutada en un documento en 'borrador'"))
            if brw_each.slip_ids:
                for brw_slip in brw_each.slip_ids:
                    brw_slip.restore_movements()
        return True

    def validate_slips(self):
        OBJ_EMPLOYEE = self.env["hr.employee"].sudo()
        for brw_each in self:
            if not brw_each.slip_ids:
                raise ValidationError(_("Debe existir al menos un rol"))
            self._cr.execute("""SELECT
                HP.EMPLOYEE_ID,COUNT(1)
            FROM HR_PAYSLIP_RUN HPR
            INNER JOIN HR_PAYSLIP HP ON HP.PAYSLIP_RUN_ID=HPR.ID
            INNER JOIN HR_CONTRACT HC ON HC.ID=HP.CONTRACT_ID
            WHERE HPR.ID=%s
            GROUP BY HP.EMPLOYEE_ID
            HAVING COUNT(1)>1 """, (brw_each.id,))
            result = self._cr.fetchall()
            if len(result) > 1:
                brw_employee = OBJ_EMPLOYEE.browse(result[0][0])
                raise ValidationError(
                    _("Solo puede existir una registro por empleado %s,%s veces en este documento") % (
                        brw_employee.name, result[0][1]))
            ###se valida documentos por reglas en el mismo mes
            self._cr.execute("""SELECT
                HP.EMPLOYEE_ID,COUNT(1)
            FROM HR_PAYSLIP_RUN HPR
            INNER JOIN HR_PAYSLIP HP ON HP.PAYSLIP_RUN_ID=HPR.ID
            INNER JOIN HR_CONTRACT HC ON HC.ID=HP.CONTRACT_ID
            WHERE HP.COMPANY_ID=%s AND HP.MONTH_ID=%s AND HP.YEAR=%s AND HP.STATE!='cancel' 
            GROUP BY HP.EMPLOYEE_ID
            HAVING COUNT(1)>1""", (brw_each.company_id.id, brw_each.month_id.id, brw_each.year))
            result = self._cr.fetchall()
            if len(result) > 1:
                brw_employee = OBJ_EMPLOYEE.browse(result[0][0])
                raise ValidationError(
                    _("Solo puede existir una registro por empleado %s para %s en el periodo en curso %s del %s.existen %s registros en este periodo.") % (
                        brw_employee.name, brw_each.rule_id.name, brw_each.month_id.name, brw_each.year, result[0][1]))

    def action_open_account_moves(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip.move",
            "views": [[False, "tree"], [False, "form"], [False, "pivot"]],
            "domain": [['payslip_run_id', '=', self.id]],
            "context": {'default_payslip_run_id': self.id, 'search_default_grp_account_id': 1},
            "name": "Detalle de Asientos",
        }

    def calculate_moves(self):
        def add_new_line_account(move_line_ids, vals, company_rules_conf, account_types=["credit", "debit"],department_id=False):
            if vals["rule_id"] in company_rules_conf:
                conf_accounts = company_rules_conf[vals["rule_id"]]
                for each_conf in conf_accounts:
                    if each_conf["account_type"] in account_types:
                        rule_vals = vals.copy()
                        rule_vals["account_id"] = each_conf["account_id"]
                        rule_vals[each_conf["account_type"]] = rule_vals["abs_total"]
                        if department_id:
                            department_srch=self.env["hr.salary.rule.account.analytic"].sudo().search(
                                [('rule_account_id.rule_id','=',vals["rule_id"]),
                                 ('rule_account_id.company_id', '=', each_conf["company_id"]),
                                 ('rule_account_id.type', '=', "payslip"),
                                 ('rule_account_id.account_id', '=', each_conf["account_id"]),
                                 ('department_id', '=', department_id),
                                 ]
                            )
                            if department_srch:
                                if len(department_srch)>1:
                                    raise ValidationError(_("Existe mas de un departamento para la configuracion de cuentas analiticas"))
                                if department_srch[0].analytic_account_id:
                                    rule_vals["analytic_account_id"]=department_srch[0].analytic_account_id.id
                                if department_srch[0].account_id:
                                    rule_vals["account_id"] = department_srch[0].account_id.id
                        move_line_ids.append((0, 0, rule_vals))
            return move_line_ids

        for brw_each in self:
            move_line_ids = [(5,)]
            self._cr.execute("""WITH DISTINCTACCOUNTS AS (
    SELECT DISTINCT HSRA.COMPANY_ID,HSRA.ACCOUNT_ID,
        HSRA.ACCOUNT_TYPE,
        HPL.SALARY_RULE_ID
    FROM
        HR_PAYSLIP_RUN HPR
        INNER JOIN HR_PAYSLIP HP ON HP.PAYSLIP_RUN_ID = HPR.ID
        INNER JOIN HR_PAYSLIP_LINE HPL ON HPL.SLIP_ID = HP.ID 
        INNER JOIN HR_SALARY_RULE_ACCOUNT HSRA ON HSRA.RULE_ID = HPL.SALARY_RULE_ID
            AND HSRA.COMPANY_ID = HP.COMPANY_ID
            AND HSRA.TYPE = 'payslip' 
    WHERE
        HPR.ID = %s
)
SELECT 
    DA.SALARY_RULE_ID AS RULE_ID,
    JSON_AGG(
        JSON_BUILD_OBJECT(
            'account_id', DA.ACCOUNT_ID,
            'account_type', DA.ACCOUNT_TYPE,
            'company_id',DA.COMPANY_ID
        )
    ) AS ACCOUNTS
FROM
    DISTINCTACCOUNTS DA 
GROUP BY  DA.SALARY_RULE_ID """, (brw_each.id,))
            result_company_rules_conf = self._cr.fetchall()
            company_rules_conf = dict(result_company_rules_conf)
            SALARY_RULE_ID = self.env.ref("gps_hr.rule_SALARIO")
            for brw_payslip in brw_each.slip_ids:
                srch_lines = self.env["hr.payslip.line"].sudo().search([
                    ('slip_id', '=', brw_payslip.id),
                    ('abs_total', '!=', 0.00),
                ])
                if srch_lines:
                    for brw_line in srch_lines:
                        account_types = ["debit", "credit"]
                        if brw_line.salary_rule_id == SALARY_RULE_ID:
                            account_types = ["debit", ]
                        vals = {
                            "payslip_run_id": brw_each.id,
                            "payslip_id": brw_line.slip_id.id,
                            "employee_id": brw_line.employee_id.id,
                            "rule_id": brw_line.salary_rule_id.id,
                            "credit": 0.00,
                            "debit": 0.00,
                            "abs_total": brw_line.abs_total,
                        }
                        add_new_line_account(move_line_ids, vals, company_rules_conf, account_types=account_types,department_id=brw_line.slip_id.department_id and brw_line.slip_id.department_id.id or False)

                if brw_payslip.total_payslip != 0.00:
                    vals = {
                        "payslip_run_id": brw_each.id,
                        "payslip_id": brw_payslip.id,
                        "employee_id": brw_payslip.employee_id.id,
                        "rule_id": SALARY_RULE_ID.id,
                        "credit": 0.00,
                        "debit": 0.00,
                        "abs_total": brw_payslip.total_payslip,
                    }
                    add_new_line_account(move_line_ids, vals, company_rules_conf, account_types=["credit"],department_id=brw_payslip.department_id and brw_payslip.department_id.id or False)
            brw_each.write({"move_line_ids": move_line_ids})

    def action_close(self):
        DEC = 2
        for brw_each in self:
            if not brw_each.date_process or brw_each.date_process is None:
                raise ValidationError(_("Debes elegir un fecha de proceso para contabilizar el Rol"))
            # Validar los slips
            brw_each.validate_slips()
            # Procesar slips si existen
            if brw_each.slip_ids:
                brw_each.slip_ids.action_validate_slips()
                brw_each.slip_ids.action_done()
            if brw_each.type_struct_id.legal_iess:
                # Inicializar totales de débito y crédito
                debit, credit = 0.00, 0.00
                # Calcular los totales de las líneas de movimiento
                for brw_move_line in brw_each.move_line_ids:
                    debit += brw_move_line.debit
                    credit += brw_move_line.credit
                # Redondear los totales
                debit = round(debit, DEC)
                credit = round(credit, DEC)
                # Validar que el débito y el crédito sean equivalentes
                if debit != credit:
                    raise ValidationError(
                        _("El debe y el haber siempre deben ser equivalentes para asegurar la correcta gestión de nuestras cuentas."))
                brw_each.create_payslip_move()
        # Llamar al metodo padre y devolver los valores
        return super(HrPayslipRun, self).action_close()

    def create_payslip_move(self):
        OBJ_MOVE = self.env["account.move"]
        OBJ_MOVE_LINE = self.env["account.move.line"]
        OBJ_RULE = self.env["hr.salary.rule"].sudo()
        for brw_each in self:
            self._cr.execute("""SELECT AM.RULE_ID,AM.analytic_account_id,
	AM.ACCOUNT_ID,
	SUM(AM.DEBIT) AS DEBIT,
	SUM(AM.CREDIT) AS CREDIT
FROM
	HR_PAYSLIP_MOVE AM
WHERE
	AM.PAYSLIP_RUN_ID = %s
GROUP BY AM.RULE_ID, AM.ACCOUNT_ID,AM.analytic_account_id """, (brw_each.id,))
            result = self._cr.fetchall()
            if result:
                vals = {
                    "move_type": "entry",
                    "name": "/",
                    'narration': brw_each.name,
                    'date': brw_each.date_process,
                    'ref': "ROL # %s,%s" % (brw_each.id, brw_each.name),
                    'company_id': brw_each.company_id.id,
                }
                if not brw_each.company_id.payslip_journal_id:
                    raise ValidationError(
                        _("Debes definir un diario de nómina para la compañia %s") % (brw_each.company_id.name,))
                vals["journal_id"] = brw_each.company_id.payslip_journal_id.id
                line_ids = [(5,)]
                for rule_id, analytic_account_id,account_id, debit, credit in result:
                    brw_rule = OBJ_RULE.browse(rule_id)
                    each_line_vals={
                        "name": brw_rule.name,
                        'debit': debit,
                        'credit': credit,
                        'ref': vals["ref"],
                        'account_id': account_id,
                        'partner_id': brw_each.company_id.partner_id.id,
                        'date': brw_each.date_process,
                        "rule_id":brw_rule.id
                    }
                    if analytic_account_id:
                        each_line_vals["analytic_distribution"]={str(analytic_account_id):100}
                    line_ids += [(0, 0, each_line_vals)]
                vals["line_ids"] = line_ids
                brw_move = OBJ_MOVE.create(vals)
                brw_move.action_post()
                if brw_move.state != "posted":
                    raise ValidationError(
                        _("Asiento contable %s,id %s no fue publicado!") % (brw_move.name, brw_move.id))
                brw_each.move_id = brw_move.id
                srch_inputs=self.env["hr.payslip.input"].sudo().search([
                    ('payslip_id.payslip_run_id','=',brw_each.id),
                    ('move_line_id','!=',False)
                ])
                #
                values_reconciles={}
                if srch_inputs:
                    for brw_input in srch_inputs:
                        if not values_reconciles.get(brw_input.rule_id,False):
                            values_reconciles[brw_input.rule_id]={
                                "account_id":self.env["account.account"],
                                "move_lines":self.env["account.move.line"],
                                "type":brw_input.rule_id.category_id.code=='IN' and 'credit' or 'debit',
                                "reverse_type": brw_input.rule_id.category_id.code == 'IN' and 'debit' or 'credit'
                            }
                        account_values_reconciles=values_reconciles[brw_input.rule_id]
                        move_lines=account_values_reconciles["move_lines"]
                        move_lines+=brw_input.move_line_id
                        account_values_reconciles["account_id"] = brw_input.move_line_id.account_id
                        account_values_reconciles["move_lines"]=move_lines
                        values_reconciles[brw_input.rule_id]=account_values_reconciles
                for each_reconcile_ky in values_reconciles:
                    each_reconcile_accounts=values_reconciles[each_reconcile_ky]
                    move_lines=each_reconcile_accounts["move_lines"]#asientos por reconciliar
                    account=each_reconcile_accounts["account_id"]
                    move_lines_srch=OBJ_MOVE_LINE.search([
                        ('move_id','=',brw_move.id),
                        ('account_id','=',account.id),
                        ('move_id.state','=','posted')
                    ])
                    (move_lines+move_lines_srch).reconcile()
            if not brw_each.move_id:
                raise ValidationError(_("No se pudo generar el asiento contable "))
            if brw_each.move_id.state != 'posted':
                raise ValidationError(_("El asiento %s debe estar en estado publicado") % (brw_each.move_id.name), )

    def test_paid(self):
        for brw_each in self:
            paid_slips=brw_each.slip_ids.filtered(lambda x: x.state=='paid' and x.total_payslip>0)
            slips = brw_each.slip_ids.filtered(lambda x: x.total_payslip > 0)
            if len(paid_slips)==len(slips):
                brw_each.write({"state":"paid"})

    def print_report(self):
        # Obtenemos la acción de reporte
        action = self.env.ref('gps_hr.report_payslip_runs_report_xlsx_act')

        if not action:
            raise  ValidationError("No se pudo encontrar el reporte.")
        data = {
            "finiquito_ids": [],
            "payslip_type": "rol",
            'rol_ids': [self.id]
        }
        # Retornamos la acción para imprimir el reporte
        return action.report_action(self,data=data)

    def send_mail_payslip(self):
        for brw_each in self:
            if brw_each.state in ("paid","close"):
                if not brw_each.slip_ids:
                    raise ValidationError(_("Al menos un empleado debe ser ingresado"))
                brw_each.write({"start_job_mail":True})
                for brw_line in brw_each.slip_ids:
                    brw_line=brw_line.with_context({"internal_type":"batch"})
                    brw_line.send_mail_payslip()
        return True

    def action_create_payment_requests(self):
        for brw_each in self:
            for brw_line in brw_each.slip_ids:
                brw_line.action_create_payment_document()
        return True

    def action_reverse_payment_request(self):
        for brw_each in self:
            if brw_each.employee_payment_ids:
                brw_each.employee_payment_ids.action_draft()
                brw_each.employee_payment_ids.write({"state":"cancelled"})
                brw_each.write({
                    'employee_payment_ids': [(5,)]
                })
        return True

    employee_payment_ids = fields.Many2many('hr.employee.payment', compute="_compute_employee_payment_ids",
                                            string='Solicitudes #')

    @api.depends('slip_ids','slip_ids.employee_payment_id')
    def _compute_employee_payment_ids(self):
        for brw_each in self:
            employee_payment_ids = self.env["hr.employee.payment"]
            if brw_each.slip_ids:
                employee_payment_ids += brw_each.slip_ids.mapped('employee_payment_id')
            employee_payment_srch = self.env["hr.employee.payment"].sudo().search([('payslip_ids', '=', brw_each.id),
                                                                                   ('state', '!=', 'cancelled')
                                                                                   ])
            if employee_payment_srch:
                employee_payment_ids += employee_payment_srch
            employee_payment_ids = employee_payment_ids.filtered(lambda x: x.state != 'cancelled')
            brw_each.employee_payment_ids = employee_payment_ids