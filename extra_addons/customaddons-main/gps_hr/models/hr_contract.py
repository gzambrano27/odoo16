# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError,UserError

FIRST_FITTEN_PAYMENT_MODE = [('percent', 'Porcentaje'), ('amount', 'Monto')]


class HrContract(models.Model):
    _inherit="hr.contract"

    struct_id=fields.Many2one("hr.payroll.structure","Estructura Salarial",compute="_get_compute_struct_id",store=False,readonly=True)
    structure_type_id = fields.Many2one("hr.payroll.structure.type", "Tipo de Estructura Salarial", compute="_get_compute_struct_id",
                                store=False, readonly=True)
    type_id=fields.Many2one("hr.contract.type",compute="_get_compute_struct_id",store=True,required=False,readonly=True)

    first_fitten_payment_mode = fields.Selection(FIRST_FITTEN_PAYMENT_MODE, string='Modo de Pago Quincena',
                                                 default='percent')
    value=fields.Float(string="Valor",digits=(16,2))
    job_id=fields.Many2one("hr.job",string="Cargo")
    ciudad_inicio = fields.Char('Ciudad', required=False)

    legal_iess = fields.Boolean(string="Para Afiliados", default=False, store=False, readonly=True,
                                related="structure_type_id.legal_iess")

    bonus_grav=fields.Monetary(string="Otros Beneficios Gravados(ig)",tracking=True,required=True,default=0.00)
    bonus = fields.Monetary(string="Otros Beneficios(i)",tracking=True, required=True, default=0.00)

    tiene_ruc = fields.Boolean(string="Tiene RUC", default=False, tracking=True,related="employee_id.tiene_ruc",store=True,readonly=False)
    calcula_iva=fields.Boolean(string="Calcula IVA", default=False, tracking=True)
    calcula_retencion = fields.Boolean(string="Calcula Retencion", default=False, tracking=True)

    retencion_fuente = fields.Float(string="% Fuente", tracking=True,default=0.00)
    retencion_iva = fields.Float(string="% IVA",   tracking=True,default=0.00)

    partner_id = fields.Many2one(related="employee_id.partner_id",store=False,readonly=True)
    ruc_partner_id = fields.Many2one(related="employee_id.ruc_partner_id",store=False,readonly=True)

    tiene_pension_alimenticia=fields.Boolean("Tiene Pension Alimenticia?",default=False,tracking=True)
    pension_alimenticia=fields.Monetary(string="Pension Alimenticia",tracking=True, required=False, default=0.00)

    @api.onchange('tiene_pension_alimenticia')
    def onchange_tiene_pension_alimenticia(self):
        if not self.tiene_pension_alimenticia:
            self.pension_alimenticia=0.00

    @api.constrains('pension_alimenticia')
    def _check_pension_alimenticia(self):
        for record in self:
            if record.pension_alimenticia < 0.00:
                raise ValidationError("La pensión alimenticia no puede ser menor a 0.00.")

    def get_contact_account(self):
        self.ensure_one()
        if self.legal_iess:
            return self.partner_id
        return self.tiene_ruc and self.ruc_partner_id or self.partner_id

    @api.onchange('contract_type_id')
    @api.depends('contract_type_id')
    def _get_compute_struct_id(self):
        for brw_each in self:
            brw_each.type_id=brw_each.contract_type_id.id
            brw_each.struct_id=brw_each.contract_type_id.struct_id and brw_each.contract_type_id.struct_id.id or False
            brw_each.structure_type_id=brw_each.contract_type_id.struct_id and brw_each.contract_type_id.struct_id.type_id.id or False

    def _generate_work_entries(self, date_start, date_stop, force=False):
        return self.env["hr.work.entry"]

    @api.model
    def get_days_contracts_end(self,employee_id):
        self._cr.execute(""";with variables as (
	select %s::int as employee_id
)

select hc.id,hc.state,hc.date_start,hc.date_end
from 
variables  
inner join hr_contract hc on hc.employee_id=variables.employee_id 
inner join hr_contract_type hct on hct.id=hc.type_id and 
	coalesce(hct.legal_iess,false)=true
where hc.state in ('close') 
order by hc.id asc""",(employee_id,))
        result=self._cr.fetchall()
        days=0
        for contract_id,state,date_start,date_end in result:
            each_result= (date_end - date_start).days + 1
            days+=each_result
        return days

    def get_current_contract_days(self,date_to=None):
        self.ensure_one()
        brw_contract=self
        date_start = fields.Date.from_string(brw_contract.date_start)
        if date_to is None:
            date_to = fields.Date.context_today(self)
        days= (date_to - date_start).days + 1
        return days

    name=fields.Char(string="# Referencia",size=255,compute="_get_compute_employee_name",store=True)

    @api.depends('employee_id', 'contract_type_id', 'company_id', 'date_start', 'date_end')
    @api.onchange('employee_id', 'contract_type_id', 'company_id', 'date_start', 'date_end')
    def _get_compute_employee_name(self):
        for brw_each in self:
            name = "%s de %s (%s al %s) para %s" % (
          brw_each.contract_type_id.name or '',  brw_each.employee_id.name or '', brw_each.date_start or '',
            brw_each.date_end or "",  brw_each.company_id.name or '')
            brw_each.name = name

    deductible_expenses_ids = fields.One2many("hr.deductible.expenses.contract.period", "contract_id", "Gastos")


    def write(self, vals):
        values = super(HrContract, self).write(vals)

        if "company_id" in vals:
            new_company_id = vals['company_id']

            for contract in self:
                # Buscar periodos relacionados a este contrato
                periods = self.env['hr.vacation.period'].search([
                    ('contract_id', '=', contract.id),
                    ('state', 'in', ['draft', 'confirmed']),
                    ('company_id', '!=', contract.company_id.id),
                    ('company_id', '=', new_company_id),
                ])

                periods._write({'company_id': contract.company_id.id})

        return values