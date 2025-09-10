# models/correos_primordialesodoo.py

from odoo import models, fields

class CorreosPrimordialesodoo(models.Model):
    _name = 'correos.primordialesodoo'
    _description = 'Correos Primordiales Odoo'

    empleado_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    name = fields.Char(string='Nombre', related='empleado_id.name', readonly=True)
    email = fields.Char(string='Correo Electrónico', related='empleado_id.work_email', readonly=True)
    departamento_id = fields.Many2one('hr.department',
                                      string='Departamento',
                                      related='empleado_id.department_id',
                                      readonly=True)
