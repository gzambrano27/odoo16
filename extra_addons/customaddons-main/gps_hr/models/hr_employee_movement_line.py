# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.tools.config import config

                
class HrEmployeeMovementLine(models.Model):
    _inherit = "hr.employee.document"
    _name="hr.employee.movement.line"
    _description="Detalle de Movimientos de Empleados"

    @api.model
    def _get_default_company_id(self):
        return self._context.get("default_company_id",False)

    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False ,default=_get_default_company_id
    )

    date_process = fields.Date("Fecha de Vencimiento", default=fields.Date.today(), required=True,tracking=True)

    category_id = fields.Many2one("hr.salary.rule.category", string="Categoría", compute="compute_category_id", store=True)


    employee_id = fields.Many2one("hr.employee", "Empleado", required=True,tracking=True)
    contract_id = fields.Many2one("hr.contract", "Contrato", required=True,tracking=True)

    type = fields.Selection([("discount", "Descuento Diferido"),
                             ("batch", "Lote Manual"),
                             ("batch_automatic", "Lote Automático")], "Tipo", required=True, default="discount",tracking=True)

    process_id=fields.Many2one("hr.employee.movement","Documento",ondelete="cascade")

    total_historic=fields.Monetary("Valor Original",digits=(16,2),default=0.00,required=True,tracking=True)
    total=fields.Monetary("Valor",digits=(16,2),default=0.01,required=True,tracking=True)
    total_to_paid=fields.Monetary("Por Aplicar",digits=(16,2),default=0.00,required=False,store=True,compute="_compute_total",tracking=True)
    total_paid=fields.Monetary("Aplicado",digits=(16,2),default=0.00,required=False,store=True,compute="_compute_total",tracking=True)
    total_pending=fields.Monetary("Pendiente",digits=(16,2),default=0.00,required=False,store=True,compute="_compute_total",tracking=True)

    quota=fields.Integer(string="Cuota",default=1,required=True,tracking=True)

    locked_edit=fields.Boolean(related="process_id.locked_edit",store=False,readonly=True)
    payment = fields.Boolean(related="process_id.payment", store=False, readonly=True)
    account = fields.Boolean(related="process_id.account", store=False, readonly=True)

    payslip_input_ids=fields.One2many("hr.payslip.input","movement_id","Aplicaciones en Nomina")

    provision_line_ids=fields.One2many("hr.employee.historic.lines","movement_line_id","Provisiones")

    payment_id=fields.Many2one('account.payment','Pago',tracking=True)

    has_payment=fields.Boolean(compute="_compute_residual_payment",string="Tiene Pago Pendiente",
                               store=True,readonly=True,default=False)

    for_payment_ids = fields.Many2many("hr.employee.payment", "payment_movement_line_rel", "movement_id",
                                         "payment_id",
                                         "Pagos", tracking=True)

    employee_payment_id = fields.Many2one('hr.employee.payment', 'Solicitudes')

    payslip_line_ids = fields.One2many('hr.employee.movement.line.payslip','movement_line_id',
                                       string='Detalle de Nomina' )

    adjust_payslip_id = fields.Many2one('hr.payslip', string='Rol a Descontar/Retribuir')

    @api.depends('payment_id','payment_id.state','payment_id.reversed_payment_id')
    def _compute_residual_payment(self):
        for brw_each in self:
            has_payment=False
            if (brw_each.payment_id and (brw_each.payment_id\
                                               and brw_each.payment_id.state=='posted' and not brw_each.payment_id.reversed_payment_id)):
                has_payment=True
            brw_each.has_payment=has_payment
            print(brw_each,brw_each.has_payment)


    def action_create_payment_document(self):
        OBJ_PAYMENT_DOC = self.env["hr.employee.payment"]
        for brw_each in self:
            brw_payment_document = OBJ_PAYMENT_DOC.create({
                "company_id": brw_each.company_id.id,
                "pay_with_transfer": brw_each.pay_with_transfer,
                "name": brw_each.name,
                "date_process": brw_each.process_id.date_process,
                "month_id": brw_each.month_id.id,
                "year": brw_each.year,
                "movement_ids": [(6, 0, [brw_each.process_id.id])],
                "movement_line_ids": [(6, 0, [brw_each.id])],
            })
            brw_payment_document.onchange_lines()
            brw_payment_document.action_sended()
            if brw_payment_document.state != 'sended':
                raise ValidationError(_("El documento de pago no pudo ser enviado!!!"))
            brw_payment_document.action_create_request()
            brw_each.employee_payment_id = brw_payment_document.id
        return True

    @api.constrains('payment_id','payment_id.state','payment_id.reversed_payment_id','has_payment')
    def update_payment_states(self):
        for brw_each in self:
            if brw_each.state=='paid' and not brw_each.has_payment:
                brw_each.state='approved'

    _order="process_id desc,id asc"

    _check_company_auto = True

    def replicate_fields_parent(self):
        self.company_id=self.process_id.company_id.id
        self.currency_id = self.process_id.currency_id.id
        self.rule_id = self.process_id.rule_id.id
        self.category_id = self.process_id.category_id.id
        self.category_code = self.process_id.category_code
        self.type = self.process_id.type
        if self.process_id.employee_id:
            self.employee_id=self.process_id.employee_id.id
        if self.process_id.contract_id:
            self.contract_id=self.process_id.contract_id.id
            self.job_id = self.process_id.contract_id.job_id.id
            self.department_id = self.process_id.contract_id.department_id.id
        else:
            self.contract_id=False
            self.job_id=False
            self.department_id=False

    @api.onchange('employee_id','date_process')
    def onchange_rule_employee_id(self):
        brw_employee = self.employee_id
        self.env["hr.employee.movement"].set_employee_info(self, brw_employee)
        self.update_date_info()
        brw_document = self
        brw_rule = brw_document.rule_id
        brw_company = brw_document.company_id
        date_process = brw_document.date_process
        OBJ_FX = self.env["dynamic.function"].sudo()
        if brw_rule:
            if brw_rule.type != 'payslip' or (brw_rule.type=='payslip' and brw_rule.for_liquidate_provision and brw_rule.enable_for_documents):
                variables = {"model_name": self._name,
                                 "brw_rule": brw_rule,
                                 "brw_company": brw_company,
                                 "brw_contract": brw_document.contract_id,
                                 "brw_employee": brw_employee,
                                 "date_process": date_process,
                                 "brw_document": brw_document
                                 }
                result = OBJ_FX.execute(brw_rule.domain_select, variables)
                self.update((result.get("result", {})))
                #########################################################
                result = OBJ_FX.execute(brw_rule.process_select, variables)
                values_update=result.get("result", {})
                if "total" in values_update:
                    values_update["total_historic"]=values_update["total"]
                print(values_update)
                self.update(values_update)
        else:
            self.name = None
            self.total=0.00
            self.total_historic=0.00

    def action_approved(self):
        for brw_each in self:
            if brw_each.total<=0.00:
                raise ValidationError(_("La linea con ID # %s debe ser mayor a 0.00 para %s cuota %s") % (brw_each.id,brw_each.employee_id.name,brw_each.quota))
            brw_each.validate_employee_values()
            if brw_each.provision_line_ids:
                brw_each.provision_line_ids.write({"state":"liquidated"})
        values =super(HrEmployeeMovementLine,self).action_approved()
        self._compute_total()
        return values

    def action_draft(self):
        for brw_each in self:
            if brw_each.provision_line_ids:
                brw_each.provision_line_ids.write({"state":"posted"})
        values =super(HrEmployeeMovementLine,self).action_draft()
        return values

    @api.onchange('total')
    def onchange_total(self):
        warning={}
        if self.total<0.00:
            self.total=0.00
            self.total_historic=0.00
            warning={"title":_("Advertencia"),"message":_("El valor ingresado debe ser superior a 0.00. Si el valor es igual a 0.00, debe ser eliminado.")}
        if warning:
            return {"warning":warning}

    @api.depends('state','payslip_input_ids','payslip_input_ids.amount',
                 'payslip_input_ids.payslip_id','payslip_input_ids.liquidation_id')
    def _compute_total(self):
        for brw_each in self:
            brw_each.update_total()

    def update_total(self):
        DEC = 2
        for brw_each in self:
            total_to_paid=0.00
            total_paid=0.00
            if brw_each.state not in ("draft","cancelled"):#paid,#approved
                total_to_paid = brw_each.total#siempre tomara el valor a pagar como reflejo de lo que debera pagar
                for brw_line in brw_each.payslip_input_ids:
                    if brw_line.payslip_id:
                        if brw_line.payslip_id.state!='cancel':
                            total_paid += brw_line.amount
                    if brw_line.liquidation_id:
                        if brw_line.liquidation_id.state!='cancelled':
                            total_paid += brw_line.amount
            brw_each.total_to_paid = round(total_to_paid, DEC)
            brw_each.total_paid = round(total_paid, DEC)
            brw_each.total_pending = round(total_to_paid-total_paid, DEC)