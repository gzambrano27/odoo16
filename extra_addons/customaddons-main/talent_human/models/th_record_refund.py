from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class AccountMoveLine(models.Model):
  _inherit = 'account.move.line'
  
  reembolso_id = fields.Many2one('hr.registro.reembolsos')
    

class ThRecordRefund(models.Model):
  _name = 'th.record.refund'
  
    
  name = fields.Char('Registro de Reembolso',default='')
  fecharegistro = fields.Date('Fecha', default=fields.Date.context_today)
  fechaingreso = fields.Date('Fecha Ingreso', default=fields.Date.context_today)
  es_empleado = fields.Boolean('Es empleado',default = True)
  partner_id = fields.Many2one("res.partner", string="Partner Employee", store=True)
  nombres = fields.Char('Nombres')
  employee_id = fields.Many2one('hr.employee', 'Empleado')
  user_id = fields.Many2one('res.users', string='User',  store=True, default=lambda self: self.env.uid, readonly=True)
  state = fields.Selection([("draft","Draft"),("approve","Approve"),("paid","Paid"),("cancel","Cancel")],"State",readonly=True, default='draft',)
  line_ids = fields.One2many('th.record.refund.line', 'reembolso_id', 'Reembolsos Lines')
  total = fields.Float('Total Reembolso', store = True)
  journal_id = fields.Many2one('account.journal', 'Income Journal', readonly=True)
  move_id = fields.Many2one('account.move', 'Mov Contable Reembolso', readonly=True)
  company_id =  fields.Many2one('res.company', 'Company', required=True, readonly=True,default = lambda self: self.env['res.company']._company_default_get('th.record.refund'))
  currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)
  pagos_ids = fields.Many2many('account.payment', string="PagosReembolsos", copy=False, readonly=True, compute='_set_pagos')
  has_pagos = fields.Boolean(help="Technical field used for usability purposes")
  val_pagado = fields.Float('Valor Pagado', digits=(16,2))
  residual = fields.Float('Residual', digits=(16,2))
  payments_widget = fields.Text()
  outstanding_credits_debits_widget = fields.Text()#(compute='_get_outstanding_info_JSON')
  has_outstanding = fields.Boolean()#(compute='_get_outstanding_info_JSON')
  move_reembolso_id = fields.Many2one('account.move', 'Mov Cruce Anticipo', readonly=True)
  tiene_combustible = fields.Boolean('Tiene Combustible')
    
    

class ThRecordRefundLine(models.Model):
  _name = 'th.record.refund.line'
  _order = 'fecha'
  
  reembolso_id = fields.Many2one('th.record.refund', 'Reembolsos', ondelete='cascade')
  beneficiario = fields.Char('Pagado a')
  tipo = fields.Many2one('th.items', 'Tipo', domain="[('otros','=',True)]")
  name_tipo=fields.Selection(related='tipo.name')
  vehicle_id = fields.Many2one('fleet.vehicle', 'Vehiculo')
  fecha = fields.Date('Fecha')
  tipo_documento = fields.Selection([('Factura','Factura'),('Vale','Vale de Caja'),('Soporte','Soporte')],    'Tipo Doc', default='Factura')
  nro_documento = fields.Char('Documento')
  observacion = fields.Char('Motivo')
  valor = fields.Float('Valor')
    
    
class account_invoice(models.Model):
  _inherit = 'account.move'
  
  beneficiario_id = fields.Many2one('res.partner', string='Beneficiario')
  vehiculo_id = fields.Many2one('fleet.vehicle', 'Vehiculo')
  journal_name = fields.Char(related = "journal_id.name", string="Diario Nombre", store=True)
 
