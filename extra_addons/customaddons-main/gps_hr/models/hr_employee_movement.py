# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.tools.config import config
import re

class HrEmployeeMovement(models.Model):
    _inherit = "hr.employee.document"
    _name = "hr.employee.movement"
    _description = "Movimientos de Empleados"



    @api.model
    def get_default_category_id(self):
        code = self.get_default_category_code()
        srch_code = self.env["hr.salary.rule.category"].sudo().search([('code', '=', code)])
        return srch_code and srch_code[0].id or False

    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company,tracking=True
    )

    type = fields.Selection([("discount", "Descuento Diferido"),
                             ("batch", "Lote Manual"),
                             ("batch_automatic", "Lote Automático")], "Tipo", required=True, default="discount",tracking=True)

    line_ids = fields.One2many("hr.employee.movement.line", "process_id", "Detalle")
    total = fields.Monetary(store=True, compute="_compute_total",tracking=True)

    total_to_paid = fields.Monetary(store=True, compute="_compute_total",tracking=True)
    total_paid = fields.Monetary(store=True, compute="_compute_total",tracking=True)
    total_pending = fields.Monetary(store=True, compute="_compute_total",tracking=True)

    locked_edit = fields.Boolean("Bloquear Modificación", default=False, compute="_compute_rule_values")
    locked_import = fields.Boolean("Bloquear Importación", default=True, compute="_compute_rule_values")
    locked_compute = fields.Boolean("Bloquear Cálculos", default=True, compute="_compute_rule_values")
    payment = fields.Boolean("Genera Pago", default=False, compute="_compute_rule_values")
    account = fields.Boolean("Contabilizar", default=False, compute="_compute_rule_values")

    category_id = fields.Many2one("hr.salary.rule.category", string="Categoría", default=get_default_category_id)

    filter_iess=fields.Boolean(string="Solo Afiliados",default=True,tracking=True)

    #amount_to_pay=fields.Monetary("Valor por Pagar",compute="_compute_amount_to_pay",store=False,readonly=False)

    _check_company_auto = True


    has_payment = fields.Boolean(compute="_compute_residual_payment", string="Tiene Pago Pendiente",
                                 store=True, readonly=True, default=False)

    amount_to_pay = fields.Monetary(compute="_compute_residual_payment", string="Saldo a Pagar",
                                 store=True, readonly=True, default=False,tracking=True)

    employee_payment_id = fields.Many2one('hr.employee.payment', 'Solicitudes #')

    employee_payment_ids= fields.Many2many('hr.employee.payment',compute="_compute_employee_payment_ids",string= 'Solicitudes #')


    @api.depends('employee_payment_id', 'line_ids.employee_payment_id' )
    def _compute_employee_payment_ids(self):
        for brw_each in self:
            employee_payment_ids=self.env["hr.employee.payment"]
            if brw_each.employee_payment_id:
                employee_payment_ids+=brw_each.employee_payment_id
            if brw_each.line_ids:
                employee_payment_ids += brw_each.line_ids.mapped('employee_payment_id')
            employee_payment_srch=self.env["hr.employee.payment"].sudo().search([('movement_ids','in',brw_each.id),
                                                                ('state','!=','cancelled')
                                                                ])
            if employee_payment_srch:
                employee_payment_ids +=employee_payment_srch
            employee_payment_ids=employee_payment_ids.filtered(lambda x:x.state!='cancelled')
            brw_each.employee_payment_ids=employee_payment_ids

    @api.depends('state','line_ids','line_ids.has_payment')
    def _compute_residual_payment(self):
        DEC=2
        for brw_each in self:
            has_payment = False
            amount_to_pay=0.00
            if brw_each.state=='approved':
                has_payment = True
                amount_paid = sum( brw_each.line_ids.filtered(lambda x :x.has_payment ).mapped('total_to_paid'))
                for brw_line in brw_each.line_ids:
                    if not brw_line.has_payment:
                        has_payment=False
                        continue
                amount_to_pay=brw_each.total_to_paid-amount_paid
            brw_each.has_payment = has_payment
            brw_each.amount_to_pay = round(amount_to_pay,DEC)

    @api.onchange('rule_id')
    def onchange_rule_id(self):
        self.update_rules()

    @api.depends('rule_id')
    def _compute_rule_values(self):
        for brw_each in self:
            brw_each.update_rules()

    def update_rules(self):
        for brw_each in self:
            locked_edit = False
            locked_import = True
            locked_compute = True
            payment = False
            account = False
            if brw_each.rule_id:
                locked_edit = brw_each.rule_id.locked_edit
                locked_import = brw_each.rule_id.locked_import
                locked_compute = brw_each.rule_id.locked_compute
                payment = brw_each.rule_id.payment
                account = brw_each.rule_id.account
            brw_each.locked_edit = locked_edit
            brw_each.locked_import = locked_import
            brw_each.locked_compute = locked_compute
            brw_each.payment = payment
            brw_each.account = account

    @api.onchange('line_ids', 'line_ids.total', 'line_ids.total_to_paid', 'line_ids.total_paid',
                  'line_ids.total_pending')
    def onchange_line_ids(self):
        self.update_total()

    @api.depends('line_ids', 'line_ids.total', 'line_ids.total_to_paid', 'line_ids.total_paid',
                 'line_ids.total_pending')
    def _compute_total(self):
        for brw_each in self:
            brw_each.update_total()

    def update_total(self):
        DEC = 2
        for brw_each in self:
            total, total_to_paid, total_paid, total_pending = 0.00, 0.00, 0.00, 0.00
            for brw_line in brw_each.line_ids:
                total += brw_line.total
                total_to_paid += brw_line.total_to_paid
                total_paid += brw_line.total_paid
                total_pending += brw_line.total_pending
            brw_each.total = round(total, DEC)
            brw_each.total_to_paid = round(total_to_paid, DEC)
            brw_each.total_paid = round(total_paid, DEC)
            brw_each.total_pending = round(total_pending, DEC)

    @api.onchange('company_id','filter_iess')
    def onchange_company_id(self):
        self.employee_id = False
        self.contract_id = False
        self.job_id = False
        self.department_id = False
        self.name = None
        self.rule_id=False
        self.line_ids = [(5,)]

    @api.onchange('company_id', 'rule_id', 'employee_id', 'contract_id', 'date_process')
    def onchange_rule_employee_id(self):
        brw_document = self
        brw_rule = brw_document.rule_id
        brw_company = brw_document.company_id
        date_process = brw_document.date_process
        brw_employee = brw_document.employee_id
        self.update_date_info()
        self.set_employee_info(self, brw_employee)
        OBJ_FX = self.env["dynamic.function"].sudo()
        if brw_rule:
            if brw_rule.type != 'payslip' or (brw_rule.type=='payslip' and brw_rule.for_liquidate_provision and brw_rule.enable_for_documents):
                brw_contract = brw_document.contract_id
                variables = {"model_name": self._name,
                             "brw_rule": brw_rule,
                             "brw_company": brw_company,
                             "brw_contract": brw_contract,
                             "brw_employee": brw_employee,
                             "date_process": date_process,
                             "brw_document": brw_document
                             }
                result = OBJ_FX.execute(brw_rule.domain_select, variables)
                self.update((result.get("result", {})))
        else:
            self.name = None
        self.line_ids = [(5,)]

    def delete_zeros(self):
        for brw_each in self:
            if brw_each.state!='draft':
                raise ValidationError(_("No puedes borrar registro con lineas en 0 si estado no es preliminar"))
            lines=brw_each.line_ids.filtered(lambda x: not x.total or x.total<=0.00)
            if lines:
                lines.unlink()
        return True

    def action_reverse_payment_request(self):

        return True

    def action_draft(self):
        for brw_each in self:
            brw_each.action_reverse_payment_request()
            if brw_each.line_ids:
                for brw_line in brw_each.line_ids:
                    brw_line.action_draft()
            if brw_each.move_id:
                if brw_each.move_id.state != 'cancel':
                    brw_each.move_id.button_draft()
                    brw_each.move_id.button_cancel()
                if brw_each.move_id.state != 'cancel':
                    raise ValidationError(_("El documento contable %s debe estar anulado") % (brw_each.move_id.name,))
                brw_each.write({"move_id":False})
        return super(HrEmployeeMovement, self).action_draft()

    def validate_acc_numbers(self,acc_number,bwr_employee):
        if not acc_number or acc_number is None:
            acc_number=""
        if not re.fullmatch(r'[0-9]+', acc_number) or re.fullmatch(r'0+', acc_number):
            raise ValidationError(
                _("La cuenta bancaria asociada para %s debe contener solo números y no ser todo ceros.") % (
                        bwr_employee.name,))

    def validate_partner_accounts(self):
        brw_each=self
        afiliado = brw_each.filter_iess
        lines=self.env['hr.employee.movement.line']
        for brw_line in brw_each.line_ids:
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

    def action_approved(self):
        for brw_each in self:
            if not brw_each.line_ids:
                raise ValidationError(_("Debes definir al menos una linea en el documento # %s") % (brw_each.id,))
            if brw_each.total <= 0.00:
                raise ValidationError(_("El total del documento # %s debe ser mayor a 0.00") % (brw_each.id,))
            if brw_each.type == "discount":
                brw_each.validate_employee_values()
                #if not brw_each.bank_account_id:
                brw_each.set_employee_info(brw_each, brw_each.employee_id)
                if not brw_each.bank_account_id:
                    raise ValidationError(
                        _("Existen registro(s) sin cuentas bancarias.Para el empleado %s") % (
                            brw_each.employee_id.name,))

                if brw_each.pay_with_transfer:
                    self.validate_acc_numbers(brw_each.employee_id.bank_account_id.acc_number, brw_each.employee_id)

                for brw_line in brw_each.line_ids:
                    brw_line.bank_account_id = brw_each.bank_account_id
                    brw_line.bank_history_id = brw_each.bank_history_id
                    brw_line.bank_acc_number = brw_each.bank_acc_number
                    brw_line.bank_tipo_cuenta = brw_each.bank_tipo_cuenta

            brw_each.validate_batchs()
            brw_each.validate_partner_accounts()
            for brw_line in brw_each.line_ids:
                brw_line.action_approved()
            super(HrEmployeeMovement, brw_each).action_approved()
            brw_each.create_movement()
            #brw_each.action_create_payment_requests()
        return True

    @api.onchange('pay_with_transfer')
    def onchange_pay_with_transfer(self):
        for brw_each in self:
            for brw_line in brw_each.line_ids:
                brw_line.pay_with_transfer = brw_each.pay_with_transfer

    def action_create_payment_requests(self):
        for brw_each in self:
            if brw_each.rule_id.payment and brw_each.rule_id.account:
                if brw_each.type == "discount":
                    brw_each.action_create_payment_document()
                else:##significa que tiene cuotas
                    for brw_line in brw_each.line_ids:
                        brw_line.action_create_payment_document()
        return True

    def action_create_payment_document(self):
        OBJ_PAYMENT_DOC=self.env["hr.employee.payment"]
        for brw_each in self:
            # if brw_each.type=='discount':
            #     self._cr.execute("""select hpp.name ,hpp.id
            #         from payment_movement_line_rel  ppr
            #         inner join hr_employee_movement_line hp on hp.id=ppr.movement_id
            #         inner join hr_employee_payment hpp on hpp.id=ppr.payment_id
            #     where ppr.movement_id=%s and hpp.state!='cancelled' """, (brw_each.id,))
            #     existing_doc = self._cr.dictfetchone()
            #     if existing_doc:
            #         raise ValidationError(_(
            #             "El rol %s ya ha sido asignado al documento de pago # %s - '%s' y no puede volver a usarse." % (
            #                 brw_each.name, existing_doc["id"], existing_doc["name"])
            #         ))
            # else:
            #     self._cr.execute("""select hpp.name ,hpp.id
            #         from payment_movement_line_rel  ppr
            #         inner join hr_employee_movement_line hp on hp.id=ppr.movement_id
            #         inner join hr_employee_payment hpp on hpp.id=ppr.payment_id
            #     where ppr.movement_id=%s and hpp.state!='cancelled' """, (brw_each.id,))
            #     existing_doc = self._cr.dictfetchone()
            #     if existing_doc:
            #         raise ValidationError(_(
            #             "El rol %s ya ha sido asignado al documento de pago # %s - '%s' y no puede volver a usarse." % (
            #                 brw_each.name, existing_doc["id"], existing_doc["name"])
            #         ))
            brw_payment_document=OBJ_PAYMENT_DOC.create({
                "company_id":brw_each.company_id.id,
                "pay_with_transfer":brw_each.pay_with_transfer,
                "name":brw_each.name,
                "date_process":brw_each.date_process,
                "month_id": brw_each.month_id.id,
                "year": brw_each.year,
                "movement_ids":[(6,0,[brw_each.id])],
                "movement_line_ids":[(6,0,brw_each.line_ids.ids)],
            })
            brw_payment_document.onchange_lines()
            brw_payment_document.action_sended()
            if brw_payment_document.state!='sended':
                raise ValidationError(_("El documento de pago no pudo ser enviado!!!"))
            brw_payment_document.action_create_request()
            brw_each.employee_payment_id=brw_payment_document.id
        return True

    def action_cancelled(self):
        for brw_each in self:
            brw_each.action_reverse_payment_request()
            if brw_each.line_ids:
                for brw_line in brw_each.line_ids:
                    brw_line.action_cancelled()
            if brw_each.move_id:
                if brw_each.move_id.state != 'cancel':
                    brw_each.move_id.button_draft()
                    brw_each.move_id.button_cancel()
                if brw_each.move_id.state != 'cancel':
                    raise ValidationError(_("El documento contable %s debe estar anulado") % (brw_each.move_id.name,))
        return super(HrEmployeeMovement, self).action_cancelled()

    def validate_batchs(self):
        OBJ_EMPLOYEE = self.env["hr.employee"].sudo()
        for brw_each in self:
            if brw_each.account and brw_each.payment:
                for brw_line in brw_each.line_ids:
                    #if not brw_line.employee_id.bank_account_id:
                    brw_line.set_employee_info(brw_line, brw_line.employee_id)
                    if not brw_line.bank_account_id:
                        raise ValidationError(
                            _("Existen registro(s) sin cuentas bancarias.El primero es %s para el movimiento %s") % (
                                brw_line.employee_id.name, brw_line.id))
                    if brw_line.pay_with_transfer:
                        self.env["hr.employee.movement"].validate_acc_numbers(brw_line.employee_id.bank_account_id.acc_number, brw_line.employee_id)

            self._cr.execute("""
             SELECT 
             HC.COMPANY_ID,COUNT(1)
             FROM HR_EMPLOYEE_MOVEMENT HEM 
             INNER JOIN HR_EMPLOYEE_MOVEMENT_LINE HEML ON HEML.PROCESS_ID=HEM.ID
             INNER JOIN HR_CONTRACT HC ON HC.ID=HEML.CONTRACT_ID
             WHERE HEM.ID=%s
             GROUP BY HC.COMPANY_ID
             """, (brw_each.id,))
            result = self._cr.fetchall()
            if len(result) > 1:
                raise ValidationError(_("Solo puede existir una compañia por documento"))
            if brw_each.rule_id.unique_month:
                ###se valida unicidad por documento
                self._cr.execute("""SELECT 
    HEML.EMPLOYEE_ID,COUNT(1)
FROM HR_EMPLOYEE_MOVEMENT HEM 
INNER JOIN HR_EMPLOYEE_MOVEMENT_LINE HEML ON HEML.PROCESS_ID=HEM.ID
INNER JOIN HR_CONTRACT HC ON HC.ID=HEML.CONTRACT_ID
WHERE HEM.ID=%s
GROUP BY HEML.EMPLOYEE_ID 
HAVING COUNT(1)>1 """, (brw_each.id,))
                result = self._cr.fetchall()
                if len(result) > 1:
                    brw_employee = OBJ_EMPLOYEE.browse(result[0][0])
                    raise ValidationError(
                        _("Solo puede existir una registro por empleado %s,%s veces en este documento") % (
                        brw_employee.name, result[0][1]))
                ###se valida documentos por reglas en el mismo mes
                self._cr.execute("""SELECT 
    HEML.EMPLOYEE_ID,COUNT(1)
FROM HR_EMPLOYEE_MOVEMENT HEM 
INNER JOIN HR_EMPLOYEE_MOVEMENT_LINE HEML ON HEML.PROCESS_ID=HEM.ID
INNER JOIN HR_CONTRACT HC ON HC.ID=HEML.CONTRACT_ID
WHERE HEM.RULE_ID=%s AND HEM.MONTH_ID=%s AND HEM.YEAR=%s
AND HEM.STATE!='cancelled'
GROUP BY HEML.EMPLOYEE_ID 
HAVING COUNT(1)>1""", (brw_each.rule_id.id, brw_each.month_id.id, brw_each.year))
                result = self._cr.fetchall()
                if len(result) > 1:
                    brw_employee = OBJ_EMPLOYEE.browse(result[0][0])
                    raise ValidationError(
                        _("Solo puede existir una registro por empleado %s para %s en el periodo en curso %s del %s.existen %s registros en este periodo.") % (
                            brw_employee.name, brw_each.rule_id.name, brw_each.month_id.name, brw_each.year,
                            result[0][1]))

        return True

    def create_movement(self):
        OBJ_MOVE = self.env["account.move"]
        for brw_each in self:
            if brw_each.account :
                vals = {
                    "move_type": "entry",
                    "name": "/",
                    'narration': brw_each.name,
                    'date': brw_each.date_process,
                    'ref': "%s ,DOCUMENTO # %s" % (brw_each.name,brw_each.id,),
                    'company_id': brw_each.company_id.id,
                }
                self._cr.execute("""SELECT AC.ACCOUNT_TYPE,
	AC.ACCOUNT_ID ,
	AC.JOURNAL_ID 
FROM HR_EMPLOYEE_MOVEMENT M
INNER JOIN HR_EMPLOYEE_MOVEMENT_LINE L ON L.PROCESS_ID=M.ID
INNER JOIN HR_SALARY_RULE R ON R.ID=L.RULE_ID
INNER JOIN HR_SALARY_RULE_ACCOUNT AC ON AC.RULE_ID=R.ID AND AC.TYPE='process' AND
	AC.COMPANY_ID=M.COMPANY_ID
WHERE L.PROCESS_ID=%s AND L.TOTAL>0 AND AC.ACCOUNT_ID IS NOT NULL
GROUP BY L.COMPANY_ID,AC.ACCOUNT_TYPE,AC.ACCOUNT_ID,
	AC.JOURNAL_ID  """, (brw_each.id,))
                result_movements = self._cr.fetchall()
                result_accounts = {x[0]: {"account_id": x[1],
                                          "journal_id": x[2]} for x in result_movements}
                line_ids = [(5,)]

                account_debits = result_accounts.get("debit", False)
                payslip_line_ids = brw_each.line_ids.mapped('payslip_line_ids')
                if not account_debits and not payslip_line_ids:
                    raise ValidationError(
                        _("No hay configuración contable para el débito para el rubro %s") % (brw_each.rule_id.name,))

                if brw_each.rule_id.type == "discount":
                    account_partner = brw_each.contract_id.get_contact_account()
                    if not account_partner:
                        raise ValidationError(
                            _("No hay contacto para la contabilizacion para %s") % (brw_each.employee_id.name,))
                    # if not brw_each.employee_id.partner_id:
                    #     raise ValidationError(
                    #         _("El empleado %s debe tener asignado un contacto") % (brw_each.employee_id.name,))
                    for brw_line in brw_each.line_ids:
                        line_ids += [(0, 0, {
                            "name": brw_line.name,
                            'debit': brw_line.total,
                            'credit': 0,
                            'ref': vals["ref"],
                            'account_id': account_debits["account_id"],
                            'partner_id': account_partner.id,
                            'date': brw_line.date_process,
                            'date_maturity': brw_line.date_process,
                            "movement_line_id": brw_line.id,
                            "rule_id":brw_line.rule_id.id
                        })]
                else:#anticipos,etc,...
                    if brw_each.rule_id.legal_iess:#se genera un valor consolidado

                        if not payslip_line_ids:
                            line_ids += [(0, 0, {
                                "name": brw_each.name,
                                'debit': brw_each.total,
                                'credit': 0,
                                'ref': vals["ref"],
                                'account_id': account_debits["account_id"],
                                'partner_id': brw_each.company_id.partner_id.id,
                                'date': brw_each.date_process,
                                #'date_maturity': brw_each.date_process,
                                "rule_id":brw_each.rule_id.id
                            })]
                        else:
                            for brw_payslip_line_payment in payslip_line_ids:
                                line_ids += [(0, 0, {
                                    "name": brw_payslip_line_payment.comments,
                                    'debit': brw_payslip_line_payment.debit,
                                    'credit':brw_payslip_line_payment.credit,
                                    'ref': brw_payslip_line_payment.comments,
                                    'account_id': brw_payslip_line_payment.account_id.id,
                                    'partner_id': brw_each.company_id.partner_id.id,
                                    'date': brw_each.date_process,
                                    #'date_maturity': brw_each.date_process,
                                    "rule_id": brw_payslip_line_payment.salary_rule_id.id
                                })]

                    else:##se identifica por cada linea
                        for brw_line in brw_each.line_ids:
                            account_partner=brw_line.contract_id.get_contact_account()
                            if not account_partner:
                                raise ValidationError(_("No hay contacto para la contabilizacion para %s") % (brw_line.employee_id.name,))
                            line_ids += [(0, 0, {
                                "name": brw_line.name,
                                'debit': brw_line.total,
                                'credit': 0,
                                'ref': vals["ref"],
                                'account_id': account_debits["account_id"],#brw_line.employee_id.partner_id.property_account_payable_id and brw_line.employee_id.partner_id.property_account_payable_id.id or account_debits["account_id"],
                                'partner_id': account_partner.id,
                                'date': brw_each.date_process,
                                #'date_maturity': brw_each.date_process,
                                "rule_id": brw_each.rule_id.id
                            })]
                account_credits = result_accounts.get("credit", False)
                if not account_credits:
                    raise ValidationError(
                            _("No hay configuración contable para el crédito para el rubro %s") % (brw_each.rule_id.name,))
                if brw_each.rule_id.category_code == "OUT":
                    vals["journal_id"] = account_debits["journal_id"]
                else:
                    vals["journal_id"] = account_credits["journal_id"]
                if not vals["journal_id"]:
                    raise ValidationError(_("No hay Diario configurado para %s") % (brw_each.rule_id.name,))
                line_ids += [(0, 0, {
                    "name": brw_each.name,
                    'credit': brw_each.total,
                    'debit': 0,
                    'ref': vals["ref"],
                    'account_id': account_credits["account_id"],
                    'partner_id': brw_each.company_id.partner_id.id,
                    'date': brw_each.date_process,
                    "rule_id":brw_each.rule_id.id
                })]
                vals["line_ids"] = line_ids
                brw_move = OBJ_MOVE.create(vals)
                brw_move.action_post()
                if brw_move.state != "posted":
                    raise ValidationError(
                        _("Asiento contable %s,id %s no fue publicado!") % (brw_move.name, brw_move.id))
                brw_each.move_id = brw_move.id

    def print_report(self):
        # Obtenemos la acción de reporte
        action = self.env.ref('gps_hr.report_movements_report_xlsx_act')
        if not action:
            raise  ValidationError("No se pudo encontrar el reporte.")
        # Retornamos la acción para imprimir el reporte
        return action.report_action(self)
