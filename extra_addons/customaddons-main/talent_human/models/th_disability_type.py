from odoo import api, fields, models, _
class ThDisabilityType(models.Model):

    _name = "th.disability.type"

    codigo = fields.Char("Codigo", size=3)
    name = fields.Char("Descripcion", size=1024)
    state = fields.Selection([('Activo','Activo'),('Inactivo','Inactivo')],    'Estado', default = 'Activo')
