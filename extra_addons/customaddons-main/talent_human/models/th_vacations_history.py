from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class ThVacationsHistory(models.Model):
    _name='th.vacations.history'
    
    
      
    
    #ref = fields.Text("Referencia")
    partner_id = fields.Many2one(related = "employee_id.partner_id",string="Proveedor")
    name = fields.Char(related = "partner_id.name",string="ID",size=60)
    #periodo =  fields.Selection(selection=lambda self: self._compute_selection(), string="Periodo",store = True)
    periodo =  fields.Char(string='Periodo')
    date = fields.Date("Inicio de Periodo")
    date_end = fields.Date("Fin de Periodo")
    employee_id = fields.Many2one("hr.employee","Empleado")
    contract_id = fields.Many2one("hr.contract", "Contrato")
    date_start = fields.Date(related = 'contract_id.date_start',string='Fecha Contrato',store = True)
    years = fields.Integer(string="Año #",store = True)
    max_days = fields.Float(string="Maximo Dias",store = True)
    days = fields.Float( string="Dias",store = True)
    dias_gozados = fields.Float(string="Dias Gozados",store = True, digits=(5,2))
    dias_pendientes = fields.Float(string="Dias Pendientes",store = True, digits=(5,2))
    state = fields.Selection([('open','Abierto'),('end','Finalizada')], "Estado", default = 'open')
    saldo_acumulado = fields.Float(string="Saldo Acumulado",store = True, digits=(5,2))
    line_ids = fields.One2many('th.vacations.history.line', 'vacation_id', 'Vacaciones Lines')
    #has_pagos = fields.Boolean(compute="tiene_pagos", help="Technical field used for usability purposes")
    has_pagos = fields.Boolean(help="Technical field used for usability purposes")
    line_provisiones_ids = fields.One2many('th.vacations.history.provisions', 'vacation_id', 'Vacaciones Provisiones')
    #para generar archivo
    csv_export_file = fields.Binary('CSV File')
    csv_export_filename = fields.Char('CSV Filename', size=50, readonly=True)
    
    _sql_constraints = [
        ('reg_vacation_uniq', 'unique(employee_id, periodo)', 'Registro de Vacacion debe ser unico!'),
    ]
    



class ThPayslipHistory(models.Model):
    _name='th.payslip.history'
     
    rule_id = fields.Many2one("th.salary.rule", "Salario")
    ref = fields.Text("Referencia")
    name = fields.Char("Nombre", size=32)
    date = fields.Date("Fecha")
    employee_id = fields.Many2one("hr.employee","Empleado")
    amount = fields.Float("Monto", digits=(16,4))
             
    
    _rec_name="date"
    
class ThVacationsHistoryProvisions(models.Model):
    _name = 'th.vacations.history.provisions'
    
    fecha_ini = fields.Date('Fecha Inicio')
    fecha_fin = fields.Date('Fecha Fin')
    vacation_id = fields.Many2one('th.vacations.history', 'Vacaciones', ondelete='cascade')
    val_provision_sueldo = fields.Float(string="Valor Provision Sueldo",store = True, digits=(6,2))
    val_provision_otro_ing = fields.Float(string="Valor Provision Otro Ingreso",store = True, digits=(6,2))
    dias = fields.Float( string="Dias",store = True)
    #payslip_id = fields.Many2one('hr.payslip', 'Payslip', ondelete='cascade')
    
class ThVacationsHistoryLine(models.Model):
    _name = 'th.vacations.history.line'
    
    vacation_id = fields.Many2one('th.vacations.history', 'Vacaciones', ondelete='cascade')
    es_pagado = fields.Boolean('Es pagado?')
    val_acumulado = fields.Float(string="Valor Acumulado",store = True, digits=(6,2))
    val_acumulado_otros_ing = fields.Float(string="Valor Acumulado Otros Ingresos",store = True, digits=(6,2))
    fecha_ini = fields.Date('Fecha Inicio Liqui Rol')
    fecha_fin = fields.Date('Fecha Fin Liqui Rol')
    fecha_ini_reg = fields.Date('Fecha Inicio Reg')
    fecha_fin_reg = fields.Date('Fecha Fin Reg')
    dias = fields.Float( string="Dias",store = True)
    holiday_id = fields.Many2one('hr.leave', 'Vacaciones', ondelete='cascade')
    state = fields.Selection([('open','Pendiente'),('end','Pagado')], "Estado", default = 'open')
    pagos_ids = fields.Many2many('account.payment', string="Pagos Vacaciones", copy=False, readonly=True, compute='_set_pagos')
    #has_pagos = fields.Boolean(compute="_get_has_pagos", help="Technical field used for usability purposes")
    has_pagos = fields.Boolean(help="Technical field used for usability purposes")
    move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True)
    #val_pagar = fields.Float(string="Valor Pagar",store = True, digits=(6,2), compute='_valor_pagar')
    val_pagado_cruzado = fields.Float(string="Valor Pagado Cruzado",store = True, digits=(6,2))
    val_residual = fields.Float(string="Valor Residual",store = True, digits=(6,2), compute='_valor_residual')
    

    
