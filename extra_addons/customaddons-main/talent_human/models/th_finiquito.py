from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class ThFiniquito(models.Model):
  _name = "th.finiquito"
  
  
  
  name = fields.Char('Nombre', size=130)
  employee_id = fields.Many2one('hr.employee','Empleado')
  date_start = fields.Date("Fecha de Ingreso")
  date_end = fields.Date("Fecha de Salida")
  decimo_tercero = fields.Float('Decimo Tercero')
  observacion_dec_ter = fields.Char('Observacion Dec Tercero')
  decimo_cuarto = fields.Float('Decimo Cuarto')
  observacion_dec_cuar = fields.Char('Observacion Dec Cuarto')
  vacaciones = fields.Float('Vacaciones')
  desahucio = fields.Float('Deshaucio')
  total = fields.Float('Total')
  state = fields.Selection([
      ('draft', 'Draft'),
      ('open', 'Open'),
      ('paid', 'Paid'),
      ('cancel', 'Cancelled'),
      ], 'Status', track_visibility='onchange', copy=False, default='draft',
      help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Voucher.\n"
            " * The 'Posted' status is used when user create voucher,a voucher number is generated and voucher entries are created in account.\n"
            " * The 'Cancelled' status is used when user cancel voucher.")
  currency_id = fields.Many2one('res.currency', 'Currency') 
  journal_id = fields.Many2one('account.journal', 'Income Journal', readonly=True)
  move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True) 
  pagos_ids = fields.Many2many('account.payment', string="Pagos Finiquito", copy=False, readonly=True)
  has_pagos = fields.Boolean(help="Technical field used for usability purposes")
    
    
    

