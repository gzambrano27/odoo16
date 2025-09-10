from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class TipoRoles(models.Model):
    _name = "tipo.roles"
    _description = 'Registro Tipos de Roles'
    
    codigo = fields.Char("Codigo", size=3)
    name = fields.Char("Tipo Rol", size=1024)
    state = fields.Selection([('ACTIVO','ACTIVO'),('INACTIVO','INACTIVO')],    'Estado', default='ACTIVO')
    

# class Tarifarios(models.Model):
#     _name = "tarifarios"
#     _description = 'Registro Maestro de Tarifarios'
    
#     name = fields.Char("Codigo", size=20)
#     tipo_rol_id = fields.Many2one('tipo.roles', 'Nombre Rol')
#     labor = fields.Char("Labores", size=1024)
#     actividad = fields.Selection([('APUNTALAR','APUNTALAR'),
#                                ('CONTROL MALEZA','CONTROL MALEZA'),
#                                ('DESHOJE','DESHOJE'),
#                                ('DRENAJES','DRENAJES'),
#                                ('ENFUNDE','ENFUNDE'),
#                                ('FERTILIZACION','FERTILIZACION'),
#                                ('OPA','OPA'),
#                                ('RIEGO','RIEGO'),
#                                ('OPA-RESIEMBRA','OPA-RESIEMBRA'),
#                                ('DESTALLADOR','DESTALLADOR'),
#                                ('PALANQUERO','PALANQUERO'),
#                                ('GARRUCHERO','GARRUCHERO'),
#                                ('ARRUMADOR','ARRUMADOR'),
#                                ('EMPAQUE','EMPAQUE'),
#                                ('GUARDIA','GUARDIA'),
#                                ('MANTENIMIENTO','MANTENIMIENTO'),
#                                ('COSECHA','COSECHA'),
#                                ('RIEGO','RIEGO'),
#                                ('ADMINISTRATIVO','ADMINISTRATIVO')
#                                ],    'Actividad', default='APUNTALAR')
#     unidad = fields.Selection([('HECTAREAS','HECTAREAS'),
#                                ('JORNAL','JORNAL'),
#                                ('CAJAS','CAJAS EMPAQUE'),
#                                ('CAJASCOSECHA','CAJAS COSECHA'),
#                                ('GRANEL','GRANEL')
#                                ],    'Unidad', default='JORNAL')
#     valor = fields.Float("Valor", digits=dp.get_precision('Product Price'))
#     state = fields.Selection([('ACTIVO','ACTIVO'),('INACTIVO','INACTIVO')],    'Estado', default='ACTIVO')
              