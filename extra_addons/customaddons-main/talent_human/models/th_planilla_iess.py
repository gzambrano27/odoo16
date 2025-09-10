from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ThPlanillaIess(models.Model):
   
  _name = 'th.planilla.iess' 
  
  name = fields.Many2one('th.transaction.type', 'Nombre', readonly=True)
  type = fields.Selection([('DESCUENTO','Retencion'),],'type')
  user_id = fields.Many2one('res.users', string='User',  store=True, default=lambda self: self.env.uid, readonly=True)
  ref = fields.Char('Ref',size=256,readonly=True)
  journal_id = fields.Many2one('account.journal', 'Income Journal', readonly=True)
  #move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True)
  user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.user)
  company_id =  fields.Many2one('res.company', 'Company', required=True, readonly=True,default = lambda self: self.env['res.company']._company_default_get('hr.discount'))
  date = fields.Date('Date register',readonly=True)
  date_from = fields.Date('Date From',readonly=True)
  amount = fields.Float('Monto', digits=(16,2), readonly=True)

  
  paid = fields.Boolean(string='Paid?')
  currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)#,default = _get_currency)
  state = fields.Selection([("draft","Draft"),("approve","Approve"),("paid","Paid"),("cancel","Cancel")],"State",readonly=True, default='draft',)
  
  observacion = fields.Text('Observacion')
  #para descuentos
  
  pagos_ids = fields.Many2many('account.payment', string="PagosPlanilla", copy=False, readonly=True, compute='_set_pagos')
  has_pagos = fields.Boolean(help="Technical field used for usability purposes")
  csv_export_file = fields.Binary('CSV File')
  csv_export_filename = fields.Char('CSV Filename', size=50, readonly=True)
  slip_run_id = fields.Many2one('hr.payslip.run', ondelete='cascade')
    
    
    

    
    