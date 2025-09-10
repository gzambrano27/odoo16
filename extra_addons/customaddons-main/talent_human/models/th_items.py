from odoo import api, fields, models, _


class ThItems(models.Model):

  _name = "th.items"

  codigo = fields.Char('Codigo', size=3)
  name = fields.Selection([('Desayuno','Desayuno'),
                            ('Almuerzo','Almuerzo'),
                            ('Merienda','Merienda'),
                            ('Combustible','Combustible'),
                            ('Valija','Envio de Valija'),
                            ('Parqueo','Parqueo'),
                            ('Lavada','Lavada de Vehiculo'),
                            ('Peaje','Peaje'),
                            ('Alimentacion','Alimentacion en Viaje'),
                            ('Lavado','Lavado de Vehiculo'),
                            ('Alquiler','Alquiler de Vehiculo'),
                            ('Movilizacion','Movilizacion Tramites de Oficina'),
                            ('Eventos','Eventos Sociales'),
                            ('Cafeteria','Cafeteria'),
                            ('Agua','Botellon de Agua'),
                            ('Limpieza','Suministros de Limpieza'),
                            ('Oficina','Suministros de Oficina'),
                            ('Medicina','Botiquin de Oficina'),
                            ('Mantenimiento','Mantenimiento de Oficina'),
                            ('Computacion','Mantenimiento de Equipos de Computo'),
                            ('Comisiones','Comisiones Bancarias'),
                            ('Tramites','Tramites Administrativos'),
                            ('Hospedaje','Viaticos por hospedaje'),
                            ('Fumigacion','Fumigacion en pista'),
                            ('Limpieza_racimo','Limpieza de Racimo'),
                            ('Devmulta','Devolucion Multa'),
                            ('Varios','Varios'),
                            ('Evafruta','Evaluacion de fruta')
                            ],    'Rubro', default='Almuerzo')
  unidad_administrativa = fields.Many2one('establecimientos', string='Unidad Administrativa')
  valor = fields.Float(digits=(4,2))
  otros = fields.Boolean('Varios')
  account_debit = fields.Many2one('account.account', 'Debit Account', domain=[('deprecated', '=', False)])
  account_credit = fields.Many2one('account.account', 'Credit Account', domain=[('deprecated', '=', False)])



class WitheListItems(models.Model):
    _name = "th.white.list.items"
    
    empleado = fields.Many2one("hr.employee", "Empleado")
    tipo_rubro = fields.Many2one("hr.rubros", "Tipos")
    reembolso = fields.Boolean("Reembolsa")
    unidad_administrativa = fields.Many2one(related = 'empleado.unidad_administrativa',store = True,string='Unidad Administrativa')
    tipo_rol = fields.Many2one(related='empleado.tipo_rol', store=True, string='Tipo Rol')
    estado = fields.Selection([
                    ('activo', 'Activo'),
                    ('inactivo', 'Inactivo'),
                    ],'Estado', default='activo')
        
    
    