# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import ValidationError

class HrEmployeeDocument(models.AbstractModel):
    _name = "hr.employee.document"
    _description = "Plantilla de Documentos de Empleados"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    @api.model
    def _get_default_company_id(self):
        if self._context.get("allowed_company_ids", []):
            return self._context.get("allowed_company_ids", [])[0]
        return False

    @api.model
    def get_default_category_code(self):
        return self._context.get("default_category_code", None)

    @api.model
    def get_default_category_id(self):
        code = self.get_default_category_code()
        srch_code = self.env["hr.salary.rule.category"].sudo().search([('code', '=', code)])
        return srch_code and srch_code[0].id or False

    name = fields.Char("Descripción", size=255, required=True)

    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one("res.currency", "Moneda",compute="compute_currency_id",store=True)

    category_code = fields.Char(string="Código de Categoría", required=True, default=get_default_category_code)
    category_id = fields.Many2one("hr.salary.rule.category", string="Categoría", default=get_default_category_id )
    rule_id = fields.Many2one("hr.salary.rule", string="Rubro", required=True)

    legal_iess = fields.Boolean(string="Para Afiliados", default=False, readonly=True, store=False,
                                related="rule_id.legal_iess")


    date_process = fields.Date("Fecha del Proceso", default=fields.Date.today(), required=True)

    month_id=fields.Many2one("calendar.month","Mes",compute="_compute_date_info",store=True,required=False)
    year=fields.Integer("Año",compute="_compute_date_info",store=True,required=False)

    comments = fields.Text("Comentarios")

    job_id = fields.Many2one("hr.job", string="Cargo", required=False)

    department_id = fields.Many2one("hr.department", string="Departamento", required=False)
    employee_id = fields.Many2one("hr.employee", "Empleado", required=False)
    contract_id = fields.Many2one("hr.contract", "Contrato", required=False)

    total = fields.Monetary("Total", digits=(16, 2), default=0.00)
    total_to_paid = fields.Monetary("Por Aplicar", digits=(16, 2), default=0.00)
    total_paid = fields.Monetary("Aplicado", digits=(16, 2), default=0.00)
    total_pending = fields.Monetary("Pendiente", digits=(16, 2), default=0.00)


    state = fields.Selection([('draft', 'Preliminar'),
                              ('approved', 'Aprobado'),
                              ('cancelled', 'Anulado'),
                              ('paid', 'Pagado')], default="draft", required=True, string="Estado")

    bank_account_id = fields.Many2one("res.partner.bank", "Cuenta de Banco", required=False)

    bank_history_id = fields.Many2one("res.bank", "Banco", compute="_compute_bank_details", store=True)
    bank_acc_number = fields.Char("# Cuenta", compute="_compute_bank_details", store=True)
    bank_tipo_cuenta = fields.Selection([
        ('Corriente', 'Corriente'),
        ('Ahorro', 'Ahorro'),
        ('Tarjeta', 'Tarjeta'),
        ('Virtual', 'Virtual')
    ], string="Tipo de Cuenta", compute="_compute_bank_details", store=True)

    @api.depends('bank_account_id','bank_account_id.bank_id','bank_account_id.acc_number','bank_account_id.tipo_cuenta')
    @api.onchange('bank_account_id', 'bank_account_id.bank_id', 'bank_account_id.acc_number',
                 'bank_account_id.tipo_cuenta')
    def _compute_bank_details(self):
        for rec in self:
            if rec.bank_account_id:
                rec.bank_history_id = rec.bank_account_id.bank_id
                rec.bank_acc_number = rec.bank_account_id.acc_number
                rec.bank_tipo_cuenta = rec.bank_account_id.tipo_cuenta  # asegúrate que este campo exista
            else:
                rec.bank_history_id = False
                rec.bank_acc_number = False
                rec.bank_tipo_cuenta = False

    origin = fields.Selection([('file', 'Archivo'),
                               ('system', 'Sistema'),
                               ('compute', 'Cálculo Automático'),
                               ('manual', 'Ingreso Manual')], string="Origen", default="manual")


    move_id=fields.Many2one("account.move",string="# Asiento")

    pay_with_transfer = fields.Boolean("Pagar con Transferencia", default=True)

    _rec_name = "name"
    _order = "id desc"

    _check_company_auto = True



    @api.depends('company_id')
    def compute_currency_id(self):
        for brw_each in self:
            brw_each.currency_id=brw_each.company_id and brw_each.company_id.currency_id.id or False

    @api.depends('rule_id')
    def compute_category_id(self):
        for brw_each in self:
            brw_each.category_id = brw_each.rule_id and brw_each.rule_id.category_id.id or False


    def action_draft(self):
        for brw_each in self:
            brw_each.write({"state":"draft"})
        return True

    def action_approved(self):
        for brw_each in self:
            brw_each.write({"state": "approved"})
        return True

    def action_cancelled(self):
        for brw_each in self:
            brw_each.write({"state": "cancelled"})
        return True

    def action_paid(self):
        for brw_each in self:
            brw_each.write({"state": "paid"})
        return True

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        brw_employee=self.employee_id
        self.set_employee_info(self,brw_employee)
        self.pay_with_transfer = brw_employee.pay_with_transfer

    @api.model
    def set_employee_info(self,obj,brw_employee):
        def clear_values(obj):
            obj.contract_id = False
            obj.job_id = False
            obj.department_id = False
            obj.bank_account_id=False
            obj.bank_history_id=False
            obj.bank_acc_number=None
            obj.bank_tipo_cuenta=None
            obj.pay_with_transfer=False
        if brw_employee:
            srch_contract=self._get_contract(brw_employee,obj.company_id)
            print(srch_contract)
            if srch_contract:
                obj.contract_id=srch_contract[0].id
                obj.job_id=srch_contract[0].job_id.id
                obj.department_id = srch_contract[0].department_id.id
                obj.bank_account_id=brw_employee.bank_account_id and brw_employee.bank_account_id.id or False

                if obj.bank_account_id:
                    obj.bank_history_id = obj.bank_account_id.bank_id
                    obj.bank_acc_number = obj.bank_account_id.acc_number
                    obj.bank_tipo_cuenta = obj.bank_account_id.tipo_cuenta
            else:
                clear_values(obj)
        else:
            clear_values(obj)

    @api.model
    def _get_contract(self,brw_employee,brw_company,raise_on=False):
        srch_contract=self.env["hr.contract"].sudo().search([('employee_id', '=', brw_employee.id),
                                                             ('company_id', '=', brw_company.id),
                                               ('state', '=', 'open')
                                               ])
        if raise_on:
            if not srch_contract:
                raise ValidationError(_("No existe contracto activo para %s para la empresa %s") % (brw_employee.name,brw_employee.company_id.name))
        return srch_contract

    @api.onchange('date_process')
    def onchange_account_date_process(self):
        self.update_date_info()

    @api.depends('date_process')
    def _compute_date_info(self):
        for brw_each in self:
            brw_each.update_date_info()

    def update_date_info(self):
        for brw_each in self:
            month_id=False
            year=False
            if brw_each.date_process:
                month_srch = self.env["calendar.month"].sudo().search([('value', '=', brw_each.date_process.month)])
                year = brw_each.date_process.year
                month_id = month_srch and month_srch[0].id or False
            brw_each.month_id=month_id
            brw_each.year = year

    def unlink(self):
        for brw_each in self:
            if self._context.get("validate_unlink", True):
                if brw_each.type == 'batch_automatic':
                    raise ValidationError(_("Documento solo se puede anular "))
                if brw_each.state != 'draft':
                    raise ValidationError(_("No puedes borrar un registro que no sea preliminar"))
        return super(HrEmployeeDocument, self).unlink()

    def validate_employee_values(self):
        for brw_each in self:
            if not brw_each.contract_id:
                raise ValidationError(_("El empleado %s debe tener activo un contrato.") % (brw_each.employee_id.name,))
            if not brw_each.department_id:
                raise ValidationError(
                        _("El contrato de %s debe tener configurado un departamento.") % (brw_each.employee_id.name,))
            if not brw_each.job_id:
                raise ValidationError(
                        _("El contrato de %s debe tener configurado un cargo.") % (brw_each.employee_id.name,))


