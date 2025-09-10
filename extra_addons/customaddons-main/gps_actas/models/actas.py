from odoo import models, fields, api
from datetime import date

class Acta(models.Model):
    _name = 'actas.acta'
    _description = 'Gestión de Actas'
    _order = 'sequence_number'

    name = fields.Char(string='Número de Acta', readonly=True)
    sequence_number = fields.Integer(string='Número Secuencial', readonly=True, index=True)
    employee_ids = fields.Many2one('hr.employee', string='Empleados')
    computer_models = fields.One2many('actas.computer', 'acta_id', string='Modelos')
    personnel = fields.One2many('actas.personnel', 'acta_id', string='Personal')
    fecha_salida_equipo = fields.Date(string='Fecha de Salida de Equipo', default=lambda self: date.today())
    fecha_recepcion_equipo = fields.Date(string='Fecha de Recepción de Equipo')
    @api.model
    def create(self, vals):
        # Calcular el siguiente número de secuencia
        vals['sequence_number'] = self.env['ir.sequence'].next_by_code('actas.sequence') or 1
        vals['name'] = f"ACTA-{str(vals['sequence_number']).zfill(4)}"
        return super().create(vals)

    def write(self, vals):
        if 'sequence_number' in vals:
            vals['name'] = f"ACTA-{str(vals['sequence_number']).zfill(4)}"
        return super().write(vals)

    @api.model
    def _renumber_actas(self):
        # Renumerar todas las actas
        actas = self.search([], order='id asc')
        for index, acta in enumerate(actas, start=1):
            acta.sequence_number = index
            acta.name = f"ACTA-{str(index).zfill(4)}"

    def unlink(self):
        # Al eliminar, renumerar las actas restantes
        res = super().unlink()
        self._renumber_actas()
        return res

class Computer(models.Model):
    _name = 'actas.computer'
    _description = 'Modelos de Computadoras'

    acta_id = fields.Many2one('actas.acta', string='Acta')
    model = fields.Char(string='Modelo')
    brand = fields.Char(string='Marca')
    serial_number = fields.Char(string='N/S')
    color = fields.Char(string='Color')

class Personnel(models.Model):
    _name = 'actas.personnel'
    _description = 'Personal'

    acta_id = fields.Many2one('actas.acta', string='Acta')
    employee_id = fields.Many2one('hr.employee', string='Empleado')
    identification_id = fields.Char(related='employee_id.identification_id', string='Cédula', readonly=True)
    job_id = fields.Many2one(related='employee_id.job_id', string='Cargo', readonly=True)
    department_id = fields.Many2one(related='employee_id.department_id', string='Departamento', readonly=True)
    company_id = fields.Many2one(related='employee_id.company_id', string='Compañía', readonly=True)
