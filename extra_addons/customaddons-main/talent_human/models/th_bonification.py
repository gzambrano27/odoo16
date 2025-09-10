from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class ThBonification(models.Model):
  _name = 'th.bonificacion'
  _inherit = ['mail.thread']
    
  name = fields.Many2one('th.transaction.type', 'Nombre', readonly=True)
  type = fields.Selection([('INGRESO','Bonificacion'),],'type')
  user_id = fields.Many2one('res.users', string='User',  store=True, default=lambda self: self.env.uid , readonly=True)
  ref = fields.Char('Ref',size=256,readonly=True)
  #partner_id = fields.Many2one('partner_id', related = 'employee_id', relation="res.partner", string="Partner Employee", store=True)
  partner_id = fields.Many2one("res.partner", string="Partner Employee", store=True)
  contract_id = fields.Many2one('hr.contract', 'Contrato')
  employee_id = fields.Many2one(related = 'contract_id.employee_id', string='Empleado', track_visibility='always')
  journal_id = fields.Many2one('account.journal', 'Income Journal', readonly=True)
  move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True)
  # user_id = fields.Many2one('res.users', 'User', states={'draft': [('readonly', False)]}, default=lambda self: self.env.user)
  company_id =  fields.Many2one('res.company', 'Company', required=True, readonly=True, states={'draft':[('readonly',False)]},default = lambda self: self.env['res.company']._company_default_get('hr.discount'))
  date = fields.Date('Date register',readonly=True)
  date_from = fields.Date('Date From',readonly=True)
  amount = fields.Float('Monto', track_visibility='always', digits=(), readonly=True,states={'draft': [('readonly', False)]})
  
  paid = fields.Boolean(method=True, string='Paid?')
  currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, states={'draft':[('readonly',False)]})#,default = _get_currency)
  state = fields.Selection([("draft","Draft"),("approve","Approve"),("paid","Paid"),("cancel","Cancel")],"State",readonly=True, default='draft',track_visibility='always')
  
  observacion = fields.Text('Observacion')
  #para descuentos
  
  pagos_ids = fields.Many2many('account.payment', string="PagosBonificacion", copy=False, readonly=True)
  has_pagos = fields.Boolean(help="Technical field used for usability purposes")
  
  #discount_id = fields.Many2one('hr.discount', 'Prestamo/Descuento')
  discount_ids = fields.One2many('th.discount.lines', 'bonificacion_id', 'Prestamos Detalle')
  total = fields.Monetary(string='Total', store=True)
  val_pagado = fields.Float('Valor Pagado', digits=(16,2))
  residual = fields.Float('Residual', digits=(16,2))
  payments_widget = fields.Text()