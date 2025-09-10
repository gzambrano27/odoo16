from odoo import api, fields, models, tools
from odoo.exceptions import UserError, ValidationError

class ThRecordItems(models.Model):
  _name = 'th.record.items'
  _inherit = ['mail.thread']
  
  tipo = fields.Many2one('th.items', 'Tipo', domain="[('otros','=',False)]")
  fecha = fields.Date('Fecha')
  fhora_ini = fields.Datetime('F. Hora Inicio')
  fhora_fin = fields.Datetime('F. Hora Fin')
  tipo_rol = fields.Many2one('tipo.roles')
  employee_id = fields.Many2one('hr.employee', 'Empleado')
  valor = fields.Float(related = 'tipo.valor', store = True)
  anio = fields.Integer('Anio')
  semana = fields.Integer(default=lambda self: self._get_semana())
  sin_reembolso = fields.Boolean('Sin Reembolso?', default=True,help="quitar check si el valor es reembolsable")
  invitado = fields.Boolean('Invitado?', default=False,help="check si es invitado")
  observacion = fields.Char('Observacion')
  reloj = fields.Selection([
      ('1', 'Matriz'),
      ('2', 'Pepa'),
      ('3', 'Marisela')
      ], 'Reloj',  default='1')
  codigoproceso  = fields.Char('Proceso')
  proceso_manual = fields.Boolean('Manual')
  
  _sql_constraints = [
      ('reg_rubros_uniq', 'unique(tipo, fecha, employee_id, observacion)', 'Registro de Rubro debe ser unico!'),
  ]
    
    
        

        
