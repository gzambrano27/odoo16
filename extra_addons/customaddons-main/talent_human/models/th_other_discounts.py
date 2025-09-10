from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class hr_otros_descuentos(models.Model):
    _name="hr.otros.descuentos"
    

    type_id = fields.Many2one("th.transaction.type","Tipo")
    sequence = fields.Integer("Secuencia")
    name = fields.Char("Numero", size=32)
    rule_id = fields.Many2one("hr.salary.rule", "Rubro")
    employee_id = fields.Many2one("hr.employee", "Empleado")
    amount = fields.Float("Monto", digits=(16,4))
    reference = fields.Text("Referencia")
    quota = fields.Integer("Cuota")
    state = fields.Selection([('draft','Borrador'),('end','Pagado')],"Estado",default = 'draft')
    iess = fields.Boolean("IESS", default = False)
    date = fields.Date('Fecha Registro', readonly=True)

    
    
    