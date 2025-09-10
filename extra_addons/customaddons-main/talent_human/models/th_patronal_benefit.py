from odoo import models, fields, api


class ThPatronalBenefit(models.Model):
  _name = 'th.patronal.benefit'
  _description = 'Patronal Benefit'

  name = fields.Many2one('th.transaction.type', 'Nombre', readonly=True,states={'draft': [('readonly', False)]})
  type = fields.Selection([('DESCUENTO','Beneficio'),],'type')
  user_id = fields.Many2one('res.users', string='User',  store=True, readonly=True)
  ref = fields.Char('Ref',size=256,readonly=True)
  #partner_id = fields.Many2one('partner_id', related = 'employee_id', relation="res.partner", string="Partner Employee", store=True)
  partner_id = fields.Many2one("res.partner", string="Partner Employee", store=True)
  #contract_id = fields.Many2one( 'hr.contract', 'Contrato')
  #employee_id = fields.Many2one(related = 'contract_id.employee_id', string='Empleado')
  employee_paid = fields.Many2one( 'hr.employee', 'Pagar a')
  journal_id = fields.Many2one('account.journal', 'Income Journal', readonly=True)
  move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True)
  user_id = fields.Many2one('res.users', 'User', states={'draft': [('readonly', False)]}, default=lambda self: self.env.user)
  company_id =  fields.Many2one('res.company', 'Company', required=True, readonly=True, states={'draft':[('readonly',False)]},default = lambda self: self.env['res.company']._company_default_get('hr.discount'))
  date = fields.Date('Date register',readonly=True,states={'draft': [('readonly', False)]})
  date_from = fields.Date('Date From',readonly=True,states={'draft': [('readonly', False)]})
  amount = fields.Float('Monto', digits=(16,2), readonly=True)

  
  paid = fields.Boolean( string='Paid?')
  currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, states={'draft':[('readonly',False)]})#,default = _get_currency)
  state = fields.Selection([("draft","Draft"),("approve","Approve"),("paid","Paid"),("cancel","Cancel")],"State",readonly=True, default='draft',)
  
  observacion = fields.Text('Observacion')
  #para descuentos
  
  pagos_ids = fields.Many2many('account.payment', string="PagosBeneficio", copy=False, readonly=True)
  has_pagos = fields.Boolean(string = 'Has Payment',help="Technical field used for usability purposes")
  csv_export_file = fields.Binary('CSV File')
  csv_export_filename = fields.Char('CSV Filename', size=50, readonly=True)