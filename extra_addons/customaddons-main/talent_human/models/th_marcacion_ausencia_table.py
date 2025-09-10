from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class TblMarcacionAusencia(models.Model):

    _name = 'th.marcacion.ausencia'
    _description = 'Tabla de Marcaciones Ausencias'
    
    employee_id = fields.Many2one('hr.employee', string = 'Empleado')
    name = fields.Char('Marcaciones Ausencia')
    nombre_empleado = fields.Char('Nombre Empleado')
    tipo_ausencia = fields.Char('Tipo Ausencia')
    marcacion_entrada = fields.Datetime('Marcacion Entrada')
    marcacion_salida = fields.Datetime('Marcacion Salida')
    ausencia_desde = fields.Datetime('Ausencia Desde')
    ausencia_hasta = fields.Datetime('Ausencia Hasta')
    horas_ausencia = fields.Float('Horas Ausencia')
    dias_ausencia = fields.Integer('Dias Ausencia')
    motivo = fields.Char('Motivo Ausencia')
    estado = fields.Char('Estado')
   