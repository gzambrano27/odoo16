from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ThRecordSmallCash(models.Model):
  _name = 'th.registro.caja.chica'
  
  name = fields.Char('Registro Caja Chica',default='')
  fecharegistro = fields.Date('Fecha')
  fechaingreso = fields.Date('Fecha Ingreso')
  es_empleado = fields.Boolean('Es empleado',default = True)
  partner_id = fields.Many2one("res.partner", string="Partner Employee", store=True)
  nombres = fields.Char('Nombres')
  employee_id = fields.Many2one('hr.employee', 'Empleado')
  user_id = fields.Many2one('res.users', string='User',  store=True, default=lambda self: self.env.uid, readonly=True)
  state = fields.Selection([("draft","Draft"),("approve","Approve"),("paid","Paid"),("cancel","Cancel")],"State",readonly=True, default='draft',)
  line_ids = fields.One2many('th.registro.caja.chica.line', 'registro_id', 'Caja Chica Lines')
  total = fields.Float('Total Caja Chica', store = True, compute='_compute_total')
  journal_id = fields.Many2one('account.journal', 'Income Journal', readonly=True)
  move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True)
  company_id =  fields.Many2one('res.company', 'Company', required=True, readonly=True,default = lambda self: self.env['res.company']._company_default_get('hr.registro.reembolsos'))
  currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)
  pagos_ids = fields.Many2many('account.payment', string="PagosCajaChica", copy=False, readonly=True)
  has_pagos = fields.Boolean(help="Technical field used for usability purposes")
    
    
    

class ThRecordSmallCashLine(models.Model):
  _name = 'th.registro.caja.chica.line'
  _order = 'fecha'
  
  registro_id = fields.Many2one('th.registro.caja.chica', 'Registro', ondelete='cascade')
  beneficiario = fields.Char('Pagado a')
  tipo = fields.Many2one('hr.rubros', 'Tipo', domain="[('otros','=',True)]")
  fecha = fields.Date('Fecha')
  tipo_documento = fields.Selection([('Factura','Factura'),('Vale','Vale de Caja'),('Soporte','Soporte')],    'Rubro', default='Factura')
  nro_documento = fields.Char('Documento')
  observacion = fields.Char('Motivo')
  valor = fields.Float('Valor')
    
  