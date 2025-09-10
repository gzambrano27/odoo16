    # -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from xlrd import open_workbook
from odoo.exceptions import ValidationError
from ...calendar_days.tools import CalendarManager,DateManager
from ...message_dialog.tools import FileManager
dtObj=DateManager()
clObj=CalendarManager()
flObj=FileManager()

class HrEmployeeMovementWizard(models.TransientModel):
    _name="hr.employee.movement.wizard"
    _description="Asistente de Movimientos Diferidos del Empleado"
    
    @api.model
    def get_default_movement_id(self):
        return self._context.get("active_ids",False) and self._context["active_ids"][0] or False
    
    @api.model
    def get_default_company_id(self):
        if self._context.get("active_ids",False):
            for brw_each in self.env["hr.employee.movement"].sudo().browse(self._context["active_ids"]):
                return brw_each.company_id.id
        return False
    
    @api.model
    def get_default_rule_id(self):
        if self._context.get("active_ids",False):
            for brw_each in self.env["hr.employee.movement"].sudo().browse(self._context["active_ids"]):
                return brw_each.rule_id.id
        return False

    @api.model
    def _get_default_legal_iess(self):
        if "active_id" not in self._context:
            return False
        srch = self.env["hr.employee.movement"].sudo().browse(self._context["active_id"])
        return srch and srch[0].rule_id.legal_iess or False

    @api.model
    def get_default_date_process(self):
        if self._context.get("active_ids",False):
            for brw_each in self.env["hr.employee.movement"].sudo().browse(self._context["active_ids"]):
                return brw_each.date_process or fields.Date.today()
        return False

    @api.model
    def get_default_origin(self):
        if self._context.get("active_ids",False):
            for brw_each in self.env["hr.employee.movement"].sudo().browse(self._context["active_ids"]):
                return brw_each.rule_id.origin
        return "file"
             
    movement_id=fields.Many2one("hr.employee.movement", "Movimiento de Empleados",required=False,default=get_default_movement_id) 
    company_id=fields.Many2one("res.company",string="Compañia",required=False,default=get_default_company_id)
    currency_id = fields.Many2one("res.currency", "Moneda", related="company_id.currency_id", store=False,
                                  readonly=True)
    rule_id=fields.Many2one("hr.salary.rule","Rubro",required=False,default=get_default_rule_id)

    legal_iess = fields.Boolean(string="Para Afiliados", default=_get_default_legal_iess)

    origin=fields.Selection([('file','Archivo'),('compute','Cálculo Automático')],string="Origen",default='file')
    file=fields.Binary("Archivo",required=False,filters='*.xlsx')
    file_name=fields.Char("Nombre de Archivo",required=False,size=255)
    amount=fields.Monetary("Monto",digits=(16,2),required=False,default=0.01)
    rate=fields.Float("% Interés",digits=(3,2),required=False,default=0.00)
    quotas=fields.Integer("# Cuotas",required=False,default=1)
    amount_rate=fields.Monetary(compute='_get_work_amounts',digits=(16,2), string='Interés',required=False)
    amount_total=fields.Monetary(compute='_get_work_amounts',digits=(16,2), string='Total',required=False)
    amount_quota=fields.Monetary(compute='_get_work_amounts',digits=(16,2), string='Monto de Cuota',required=False)
    date_process=fields.Date("Fecha de Corte",required=False,default=get_default_date_process)

    employee_ids=fields.Many2many("hr.employee","employee_movement_wizard_rel","wizard_id","employee_id","Empleados")

    @api.depends('amount','quotas','rate')
    def _get_work_amounts(self):
        for brw_each in self:
            brw_each.compute_amounts()

    @api.onchange('amount','quotas','rate')
    def onchange_amount(self,):
        values={}
        warning={}
        if self.amount<=0:
            self.amount=0.01
            warning={"title":_("Error"),"message":_("Monto no puede ser menor a 0.01")}
        if self.quotas<=0:
            self.quotas=1
            warning={"title":_("Error"),"message":_("# Cuotas debe ser mayor o igual a 1 ")}
        if self.rate<0:
            self.rate=0
            warning={"title":_("Error"),"message":_("% Interés debe ser mayor o igual a 0.00 ")}
        self.compute_amounts()
        if warning:
            values["warning"]=warning
        return values

    def compute_amounts(self):
        DEC = 2
        for brw_each in self:
            amount_quota = 0.00
            amount_rate = round((brw_each.amount * brw_each.rate / 100.00), DEC)
            brw_each.amount_rate = amount_rate
            brw_each.amount_total = round(brw_each.amount_rate + brw_each.amount, DEC)
            if brw_each.quotas > 0:
                amount_quota = round(brw_each.amount_total / float(brw_each.quotas), DEC)
            brw_each.amount_quota = amount_quota

    def process_discount(self):
        for brw_each in self:
            brw_each.movement_id.write({"origin":brw_each.origin})
            if brw_each.origin=="file":
                brw_each.process_file_discount()
            else:
                brw_each.process_compute_discount()
        return True
        
    def process_compute_discount(self):
        self._cr.execute("SELECT VALUE,ID FROM CALENDAR_MONTH")
        result=self._cr.fetchall()
        DCT_MONTHS=dict(result)
        DEC=2
        for brw_each in self:
            new_date_process=brw_each.date_process
            total=0.00
            totalglobal=0.00
            amount=brw_each.amount_quota
            line_ids=[(5,)]
            for each_range in range(0,brw_each.quotas):
                quota=each_range+1
                new_date_process_temp=new_date_process
                if each_range>0:
                    new_date_process_temp=dtObj.addMonths(new_date_process, each_range)
                dayTemp= new_date_process.day
                dayTop=clObj.days(new_date_process_temp.year, new_date_process_temp.month)
                if dayTemp>dayTop:
                    dayTemp=dayTop                    
                datevalue=dtObj.create(new_date_process_temp.year, new_date_process_temp.month,dayTemp)
                total+=round(amount,DEC)
                if brw_each.quotas==each_range+1:
                    amount=round(amount+round((brw_each.amount_total-total),DEC),DEC)
                totalglobal+=round(amount,DEC)
                brw_employee=brw_each.movement_id.employee_id
                brw_contract=brw_each.movement_id.contract_id
                values={
                        "company_id":brw_each.company_id.id,
                        "rule_id":brw_each.rule_id.id,
                        "category_code":brw_each.movement_id.category_code,
                        "date_process":datevalue ,
                        "year":datevalue.year,
                        "month_id":DCT_MONTHS[datevalue.month],
                        "employee_id":brw_employee.id,
                        "contract_id":brw_contract.id,
                        "name":brw_each.movement_id.name,
                        "comments":_("CUOTA CALCULADA AUTOMATICAMENTE"),
                        "department_id":brw_contract.department_id.id,
                        "job_id":brw_contract.job_id.id,
                        "bank_account_id":brw_employee.bank_account_id and brw_employee.bank_account_id.id or False,
                        "origin":"compute",
                        "total":amount,
                        "total_historic":amount,
                        "quota":quota,
                        "type":brw_each.movement_id.type
                }
                line_ids.append((0,0,values))
                if totalglobal>brw_each.amount_total:
                    continue               
            brw_each.movement_id.write({"line_ids":line_ids})
        return True

    def process_file_discount(self):
        self._cr.execute("SELECT VALUE,ID FROM CALENDAR_MONTH")
        result = self._cr.fetchall()
        DCT_MONTHS = dict(result)
        DEC = 2
        DATE,AMOUNT=0,1
        for brw_each in self:
            type_error=0
            error_message=False
            line_ids = [(5,)]
            ext=flObj.get_ext(brw_each.file_name)
            fileName=flObj.create(ext)
            flObj.write(fileName,flObj.decode64((brw_each.file)))
            book = open_workbook(fileName)
            sheet = book.sheet_by_index(0)
            quota=1
            for row_index in range(0, sheet.nrows):
                amount=float(str(sheet.cell(row_index, AMOUNT).value))
                str_date=str(sheet.cell(row_index, DATE).value)
                datevalue=dtObj.parse(str_date)
                brw_employee = brw_each.movement_id.employee_id
                brw_contract = brw_each.movement_id.contract_id
                values = {
                    "company_id": brw_each.company_id.id,
                    "rule_id": brw_each.rule_id.id,
                    "category_code": brw_each.movement_id.category_code,
                    "date_process": datevalue,
                    "year": datevalue.year,
                    "month_id": DCT_MONTHS[datevalue.month],
                    "employee_id": brw_employee.id,
                    "contract_id": brw_contract.id,
                    "name": brw_each.movement_id.name,
                    "comments": _("CUOTA IMPORTADA DESDE ARCHIVO"),
                    "department_id": brw_contract.department_id.id,
                    "job_id": brw_contract.job_id.id,
                    "bank_account_id": brw_employee.bank_account_id and brw_employee.bank_account_id.id or False,
                    "origin": "file",
                    "total": amount,
                    "total_historic": amount,
                    "quota": quota,
                    "type":brw_each.movement_id.type
                }
                line_ids.append((0, 0, values))
                quota+=1
            brw_each.movement_id.write({"line_ids":line_ids})
        return True

    def process(self):
        for brw_each in self:
            brw_each.movement_id.write({"origin":brw_each.origin})
            if brw_each.origin=="file":
                brw_each.process_file()
            else:
                brw_each.process_compute()
        return True

    def process_file(self):
        OBJ_EMPLOYEE = self.env["hr.employee"].sudo()
        ID, NAME, QUOTA, AMOUNT, COMMENTS = 0, 1, 2, 3, 4
        for brw_each in self:
            line_ids = [(5,)]
            ext=flObj.get_ext(brw_each.file_name)
            fileName=flObj.create(ext)
            flObj.write(fileName,flObj.decode64((brw_each.file)))
            book = open_workbook(fileName)
            sheet = book.sheet_by_index(0)
            for row_index in range(0, sheet.nrows):
                employee_identification = str(sheet.cell(row_index, ID).value).replace('.0', '')
                if len(employee_identification) == 9:
                    employee_identification = "0" + employee_identification
                employee_name = sheet.cell(row_index, NAME).value
                amount = float(str(sheet.cell(row_index, AMOUNT).value))
                quota = int(float(str(sheet.cell(row_index, QUOTA).value)))
                comments = sheet.cell(row_index, COMMENTS).value
                comments = comments and str(comments) or _("MOVIMIENTO IMPORTADO DESDE ARCHIVO")
                srch_employee = OBJ_EMPLOYEE.search([('identification_id', '=', employee_identification)])
                if not srch_employee:
                    #type_error = 1
                    error_message = _("Empleado %s con id %s no existe.Fila %s") % (
                    employee_name, employee_identification, row_index)
                    continue
                if len(srch_employee) > 1:
                    #type_error = 1
                    error_message = _("Existe más de un empleado con ese ID %s.Nombre %s y fila %s") % (
                    employee_identification, employee_name, row_index)
                    continue
                brw_employee = srch_employee[0]
                brw_contract = brw_each.movement_id._get_contract(brw_employee,brw_each.company_id,raise_on=True)
                if brw_contract:
                    brw_contract=brw_contract[0]
                values = {
                    "company_id": brw_each.company_id.id,
                    "rule_id": brw_each.rule_id.id,
                    "category_code": brw_each.movement_id.category_code,
                    "date_process":  brw_each.movement_id.date_process,
                    "year":  brw_each.movement_id.year,
                    "month_id":  brw_each.movement_id.month_id.id,
                    "employee_id": brw_employee.id,
                    "contract_id": brw_contract.id,
                    "name": brw_each.movement_id.name,
                    "comments": comments,
                    "department_id": brw_contract.department_id.id,
                    "job_id": brw_contract.job_id.id,
                    "bank_account_id": brw_employee.bank_account_id and brw_employee.bank_account_id.id or False,
                    "origin": "file",
                    "total": amount,
                    "total_historic": amount,
                    "quota": quota,
                    "type":brw_each.movement_id.type
                }
                line_ids.append((0, 0, values))
                quota+=1
            brw_each.movement_id.write({"line_ids":line_ids})
        return True

    def process_compute(self):
        DEC=2
        for brw_each in self:
            line_ids = [(5,)]
            for brw_employee in brw_each.employee_ids:
                brw_contract = brw_each.movement_id._get_contract(brw_employee,brw_each.company_id,raise_on=True)
                if brw_contract:
                    brw_contract = brw_contract[0]
                quota=1
                values = {
                    "company_id": brw_each.company_id.id,
                    "rule_id": brw_each.rule_id.id,
                    "category_code": brw_each.movement_id.category_code,
                    "date_process": brw_each.movement_id.date_process,
                    "year": brw_each.movement_id.year,
                    "month_id": brw_each.movement_id.month_id.id,
                    "employee_id": brw_employee.id,
                    "contract_id": brw_contract.id,
                    "name": brw_each.movement_id.name,
                    "comments": _("CUOTA CALCULADA AUTOMATICAMENTE"),
                    "department_id": brw_contract.department_id.id,
                    "job_id": brw_contract.job_id.id,
                    "bank_account_id": brw_employee.bank_account_id and brw_employee.bank_account_id.id or False,
                    "origin": "compute",
                    "total": 0.00,
                    "total_historic": 0.00,
                    "quota": quota,
                    "type":brw_each.movement_id.type
                }
                line_ids.append((0, 0, values))
            brw_each.movement_id.write({"line_ids": line_ids})
            for brw_line in brw_each.movement_id.line_ids:
                brw_line.onchange_rule_employee_id()
        return True

    @api.onchange('company_id')
    def onchange_company_id(self):
       self.employee_ids=[(6,0,[])]
