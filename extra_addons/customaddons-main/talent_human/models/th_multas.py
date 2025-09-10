from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ThMultas(models.Model):
    _name="th.multas"
    

    type_id = fields.Many2one("th.transaction.type","Tipo")
    sequence = fields.Integer("Secuencia")
    name = fields.Char("Numero", size=32)
    rule_id = fields.Many2one("th.salary.rule", "Rubro")
    employee_id = fields.Many2one("th.employee", "Empleado")
    amount = fields.Float("Monto", digits=(16,4))
    reference = fields.Text("Referencia")
    quota = fields.Integer("Cuota")
    state = fields.Selection([('draft','Borrador'),('end','Pagado')],"Estado",default = 'draft')
    iess = fields.Boolean("IESS", default = False)
