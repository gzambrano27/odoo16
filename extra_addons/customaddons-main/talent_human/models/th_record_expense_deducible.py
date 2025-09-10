from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class ThExpenseDeducibleHistory(models.Model):
  _name = "th.expense.deducible.history"
  _description = "Gastos Historicos deducibles empleados"

  gasto_id =  fields.Many2one('th.record.expense.deducible',string='Contract Gasto', ondelete="cascade")
  name = fields.Datetime(string='Date')
  valor_gasto = fields.Float(digits=(16,2),string='gasto')
  user_id = fields.Many2one('res.users', 'User',default = lambda self: self.env.user)
    
    

class ThRecordExpenseDeducible(models.Model):
  _name = 'th.record.expense.deducible'
  #_order = "last_name asc, mother_last_name asc, first_name asc, second_name asc"
  
  
  name = fields.Char('Gastos Empleado',store = True)
  fecha_registro = fields.Date("Fecha Registro")
  contrato_id = fields.Many2one('hr.contract', 'Empleado', help="Empleado",store = True)
  anio_id = fields.Many2one('anio.deducible', 'Anio', help="Anio",store = True, domain="[('active','=',True)]")
  sueldo = fields.Float(string='Sueldo',store = True)
  compensacion_35 = fields.Float(string='Compensacion 35%',store = True)
  compensacion_35_anual = fields.Float(string='Compensacion 35% Anual',store = True)
  otros_ingresos = fields.Float(string='Beneficios de Orden Social',store = True)
  comision = fields.Float(string='Comision',store = True)
  otras_comisiones_anual = fields.Float(string='Otras Comisiones Anual',store = True)
  sueldo_anual = fields.Float(string='Sueldo Anual',store = True)
  otros_ingresos_anual = fields.Float(string='Otros Ingresos Anual',store = True)
  bonificacion = fields.Float(string='Bonificacion',store = True)
  utilidades = fields.Float(string='Utilidades',store = True)
  utilidad_retencion_judicial = fields.Float(string='Utilidad Retencion Judicial',store = True)
  aporte_personal_iess = fields.Float(string='Aporte IESS',store = True)
  vivienda = fields.Float(string='Vivienda',store = True)
  educacion = fields.Float(string='Educacion',store = True)
  salud = fields.Float(string='Salud',store = True)
  vestimenta = fields.Float(string='Vestimenta',store = True)
  alimentacion = fields.Float(string='Alimentacion',store = True)
  turismo = fields.Float(string='Turismo',store = True)
  cargas = fields.Integer(string='Numero Cargas',store = True, compute='_numero_cargas')
  state = fields.Selection([('open','Abierto'),('end','Finalizada')], "Estado", default = 'open')
  calculo_gastos_lines = fields.One2many('hr.calculo.reg.gastos.deducibles', 'calculo_id', 'Gastos Deducibles')
  ingresos_otros_empleadores = fields.Float(string='Ingresos Otros Empleadores',store = True)
    
    
    
    
class hrCalculoGastosDeducibles(models.Model):
  _name = 'hr.calculo.reg.gastos.deducibles'
  
  calculo_id = fields.Many2one('hr.registro.gastos.deducibles', 'Gastos', help="Gastos",store = True, ondelete="cascade")
  sueldo = fields.Float(string='Sueldo',store = True)
  sueldo_acumulado = fields.Float(string='Sueldo acumulado',store = True)
  otros_ingresos = fields.Float(string='Beneficios de Orden Social',store = True)
  otros_ingresos_acumulado = fields.Float(string='Otros Ingresos acumulado',store = True)
  sueldo_anual = fields.Float(string='Sueldo Anual',store = True, compute='_sueldo_anual')
  otros_ingresos_anual = fields.Float(string='Otros Ingresos Anual',store = True)
  comision = fields.Float(string='Comision',store = True)
  comisiones_anual = fields.Float(string='Comisiones Anual',store = True)
  comisiones_acumulado = fields.Float(string='Comisiones Acumulado',store = True)
  bonificacion = fields.Float(string='Bonificacion',store = True)
  num_horas_extras_50 = fields.Float(string='#Horas 50%',store = True)
  val_horas_extras_50 = fields.Float(string='Valor Horas 50%',store = True)
  num_horas_extras_100 = fields.Float(string='#Horas 100%',store = True)
  val_horas_extras_100 = fields.Float(string='Valor Horas 100%',store = True)
  utilidades = fields.Float(string='Utilidades',store = True)
  aporte_personal_iess = fields.Float(string='Aporte IESS',store = True)
  aporte_personal_iess_anual = fields.Float(string='Aporte IESS anual',store = True)
  aporte_personal_iess_acumulado = fields.Float(string='Aporte IESS anual',store = True)
  base_imponible = fields.Float(string='Base Imponible',store = True)
  fraccion_basica = fields.Float(string='Fraccion Basica',store = True)
  impuesto_fraccion_basica = fields.Float(string='Impuesto Fraccion Basica',store = True)
  excedente = fields.Float(string='Excedente',store = True)
  impuesto_fraccion_excedente = fields.Float(string='Impuesto Fraccion Excedente',store = True)
  total_impuesto = fields.Float(string='Total Impuesto',store = True)
  total_impuesto_descontar = fields.Float(string='Total Impuesto Descontar',store = True)
  impuesto_mensual_descontar = fields.Float(string='Impuesto Mensual Descontar',store = True)
  impuesto_mensual_descontar_acumulado = fields.Float(string='Impuesto Mensual Descontar acumulado',store = True)
  slip = fields.Many2one('hr.payslip', 'Nomina', help="Nomina",store = True, ondelete="cascade")
  fecha_desde = fields.Date('Fecha desde')
  fecha_hasta = fields.Date('Fecha hasta')
  rebaja_gastos_personales = fields.Float(string='Rebaja Gastos Personales',store = True)
  impuesto_renta_pagar = fields.Float(string='Impuesto Renta Pagar',store = True)
  vacacion = fields.Float(string='Vacacion',store = True)
  compensacion = fields.Float(string='Vacacion',store = True)
  compensacion_acumulado = fields.Float(string='Vacacion',store = True)
    
    
    
    