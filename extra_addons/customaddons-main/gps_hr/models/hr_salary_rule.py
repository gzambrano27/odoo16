# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError,UserError

class HrSalaryRule(models.Model):    
    _inherit="hr.salary.rule"
    
    struct_id=fields.Many2one("hr.payroll.structure",required=False,ondelete="set null")
    active=fields.Boolean("Activo",default=True)
    category_id=fields.Many2one("hr.salary.rule.category",string="Categoría")
    
    amount_select=fields.Selection(default="code")
    condition_select=fields.Selection(default="python")
    
    process_select=fields.Text("Calculo de Proceso",default="""result={"total":0.01}""")
    domain_select=fields.Text("Condición de Proceso",default="""result={} """)
    
    add_iess=fields.Boolean("Agregar IESS",default=False)
    
    locked_edit=fields.Boolean("Bloquear Modificación",default=False)
    locked_import=fields.Boolean("Bloquear Importación",default=True)
    locked_compute = fields.Boolean("Bloquear Cálculos", default=True)

    category_code=fields.Char(related="category_id.code",string="Código de Categoría")
    
    type=fields.Selection([("payslip","Solo Nómina"),
                           ("discount","Descuento Diferido"),
                           ("batch","Lote Manual"),
                           ("batch_automatic","Lote Automático"),
                           ("liquidation","Finiquito")], "Tipo",required=True,default="payslip")
    
    force_payslip=fields.Boolean("Forzar en Rol",default=False)
    show_print=fields.Boolean("Mostrar en Impresión de Rol",default=True)
    
    payment=fields.Boolean("Genera Pago",default=False)
    account=fields.Boolean("Contabilizar",default=False,help="Genera un Asiento")

    unique_month=fields.Boolean("Único por Periodo",default=False)

    legal_iess = fields.Boolean(string="Para afiliados",default=True)

    for_liquidate_provision=fields.Boolean(string="Para liquidar Prov.",default=False)
    provision_rule_ids=fields.Many2many("hr.salary.rule","provision_hr_salary_rule_rel","rule_id","provision_id",string="Reglas de Provision")
    enable_for_documents=fields.Boolean("Habilitar para generar Documentos",default=False)

    process_liquidation_select = fields.Text("Calculo de Liquidación", default="""result=amount_factor""")
    domain_liquidation_select = fields.Text("Condición de Liquidación", default="""amount,amount_factor,result=brw_liquidation.sum_by_rules(brw_rule)""")


    @api.onchange('payment')
    def onchange_payment(self):
        if self.payment:
            self.account=True

    @api.onchange('type')
    def onchange_type(self):
        self.force_payslip = (self.type!="discount")

    @api.model
    def _get_default_help_programming_code(self):
        return self.env["dynamic.function"].sudo()._get_default_help_programming_code()

    def _compute_help_programming_code(self):
        for brw_each in self:
            help_programming_code = self._get_default_help_programming_code()
            brw_each.help_programming_code = help_programming_code

    help_programming_code = fields.Text(compute='_compute_help_programming_code', string="Ayuda de Programación",
                                        readonly=False, store=False, default=_get_default_help_programming_code)

    rule_account_ids=fields.One2many("hr.salary.rule.account","rule_id","Cuentas")

    _sql_constraints = [] 
    
    _order="category_id asc,sequence asc"
       
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args = []
        search_ids=[]
        if name:
            search_ids = self.search( [('code',operator,name)] + args, limit=limit)
        if not search_ids:
            search_ids = self.search( [('name',operator,name)] + args, limit=limit)        
        result= (search_ids is not None) and search_ids.name_get() or []
        return result   
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        result= models.Model.search_read(self, domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.returns('self', lambda value:value.id)
    def copy(self, default=None):
        raise ValidationError(_("No puedes duplicar este documento"))
    
    @api.model
    def create(self, vals):
        brw_new= super(HrSalaryRule,self).create(vals)
        brw_new.validate_configuration()
        return brw_new
     
    def write(self, vals):
        value= super(HrSalaryRule,self).write(vals)
        for brw_each in self:
            brw_each.validate_configuration()
        return value
    
    def validate_configuration(self):
        if self._context.get("validate_rules",False):
            for brw_each in self:
                pass
        return True

    @api.model
    def get_default_values(self,brw_company,brw_rule,brw_document,model_name,date_process,brw_employee=None,brw_contract=None):
        result={}
        name = ("%s DEL MES DE %s DEL %s" % (brw_rule.name, brw_document.month_id.name, str(brw_document.year))).upper()
        if model_name in ('hr.employee.movement.line', 'hr.employee.movement'):
            if model_name == 'hr.employee.movement.line' and (brw_employee is not None and brw_employee):
                name = "%s DE %s" % (name, brw_employee.name or '..',)
            result = {"name": name, }
        return result

    @api.model
    def get_default_yearly_values(self, brw_company, brw_rule, brw_document, model_name, date_process, brw_employee=None,
                           brw_contract=None):
        result = {}
        name = ("%s DEL %s" % (brw_rule.name, str(brw_document.year))).upper()
        if model_name in ('hr.employee.movement.line', 'hr.employee.movement'):
            if model_name == 'hr.employee.movement.line' and (brw_employee is not None and brw_employee):
                name = "%s DE %s" % (name, brw_employee.name or '..',)
            result = {"name": name, }
        return result

    def _new_satisfy_condition(self, localdict):
        OBJ_FX = self.env["dynamic.function"].sudo()
        result = OBJ_FX.execute(self.condition_python, localdict)
        return result.get("result",False),result.get("amount",0.00),result.get("amount_factor",0.00)

    def _new_compute_rule(self, localdict):
        OBJ_FX = self.env["dynamic.function"].sudo()
        result = OBJ_FX.execute(self.amount_python_compute, localdict)
        return result.get("result", 0.00),1.00,100.00

    def _new_satisfy_liquidation_condition(self, localdict):
        OBJ_FX = self.env["dynamic.function"].sudo()
        result = OBJ_FX.execute(self.domain_liquidation_select, localdict)
        return result.get("result",False),result.get("amount",0.00),result.get("amount_factor",0.00)

    def _new_compute_liquidation_rule(self, localdict):
        OBJ_FX = self.env["dynamic.function"].sudo()
        result = OBJ_FX.execute(self.process_liquidation_select, localdict)
        return result.get("result", 0.00),1.00,100.00