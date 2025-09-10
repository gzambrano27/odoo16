from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class RegistroCruceAsiento(models.Model):
  _name = 'registro.cruce.asientos'
  _description = 'Registro de detalle de Cruce de Asientos'
  
  payslip_run_id = fields.Many2one('hr.payslip.run', 'Rol General', ondelete='cascade')
  fecha_abono = fields.Date('Fecha Abono', default=fields.Date.context_today)
  motivo = fields.Text(string='Description')
  valor_abono = fields.Float(string='Valor Cruce', digits=(16, 2))
  #tipo = fields.Selection([('transporte', 'Abono Transporte'),('notacredito', 'Nota de Credito')], 'Tipo Abono')
  #account_id = fields.Many2one('account.account')
  move_id = fields.Many2one('account.move', ondelete='cascade')
  state = fields.Selection([('cruzado', 'Cruzado'),('pendiente', 'Pendiente Cruzar')], 'Estado', default= 'pendiente')
  user_id = fields.Many2one('res.users', string='User',  store=True, default=lambda self: self.env.uid, readonly=True)

class TblTemporalCtasRol(models.TransientModel):

  _name = 'tbl.cuentas.rol'
  _description = 'Tabla Temporal Cuentas'
  
  name = fields.Char('Nombre')
  debit = fields.Float('Debito')
  credit = fields.Float('Credito')
  reference = fields.Char('Referencia')
  account_id = fields.Many2one('account.account')
  move_id = fields.Many2one('account.move')
  journal_id = fields.Many2one('account.journal')
  period = fields.Integer('Periodo')
  partner_id = fields.Many2one('res.partner')
  date = fields.Date('Fecha')
   

class hr_payslip_run(models.Model):
  _inherit = 'hr.payslip.run'
  _rec_name = 'reference'
  
  
  
  company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id, store=True)
  partner_company_id = fields.Many2one(related = 'company_id.partner_id', string="Name", store=True)
  reference = fields.Char('Name', size=64)
  days = fields.Float('Work Days', digits=(16, 2))
  data = fields.Binary('File')
  move_id = fields.Many2one('account.move', 'Accounting Entry')
  move_id_iess = fields.Many2one('account.move', 'Accounting Entry Iess')
  move_id_cruce = fields.Many2one('account.move', 'Mov. Cruce')
  bank_account_id = fields.Many2one("res.partner.bank","Account Bank")
  total = fields.Float(string='Total of Payslip', digits = (16,2), multi='total')
  total_bank = fields.Float(string='Total of Payslip of Bank', digits=(16,2), multi='total')
  name = fields.Char('Name', size=64)
  journal_id = fields.Many2one('account.journal', 'Diario de Nomina')#,default=lambda self: self._get_journal()
  
  pagos_ids = fields.Many2many('account.payment', string="PagosRol", copy=False, readonly=True)
  has_pagos = fields.Boolean(help="Technical field used for usability purposes")
  state = fields.Selection(selection_add=[('paid', 'Pagado')])
  csv_export_file = fields.Binary('CSV File')
  csv_export_filename = fields.Char('CSV Filename', size=50, readonly=True)
  rol_agricola = fields.Boolean('Rol Agricola')
  rol_empaque = fields.Boolean('Rol Empaque')
  discontinuo = fields.Boolean('Discontinuo')
  residual = fields.Float('Residual', digits=(16,2), store= True)
  val_pagado = fields.Float('Valor Pagado', digits=(16,2), store=True)
  payments_widget = fields.Text()
  slip_ids = fields.One2many('hr.payslip', 'payslip_run_id', string='Payslips', readonly=False)
  asiento_ids = fields.One2many('registro.cruce.asientos', 'payslip_run_id', string='Payslips', readonly=False)
  aplica_abono = fields.Boolean('Aplica Abono?')
  total_abonos = fields.Float(string='Total Abonos')
    
    


class CalculoReglasRolPago(models.TransientModel):
    _name = 'calculo.regla.rol'
    _description = 'Calculo de reglas de rol'

    company_id = fields.Many2one('res.company', string='Company')
    rol_pago = fields.Many2one('hr.payslip', string='Rol')
    regla_salarial = fields.Many2one('hr.salary.rule',string='Regla salarial')
    total = fields.Float('Total')
    linea_det_pag=fields.Many2one('hr_payslip_line',string='Linea detalle pago')
    
