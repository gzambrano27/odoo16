from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Seccion(models.Model):
    _name = 'planillas.seccion'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Sección'

    name = fields.Char(string='Nombre', tracking=True)
    codigo = fields.Char(string='Código', copy=False, default=lambda self: 'New')
    estado = fields.Selection([
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo')
    ], string='Estado', default='activo', tracking=True)

    @api.model
    def create(self, vals):
        # Validar que no haya otro registro con el mismo nombre
        if 'name' in vals and self.env['planillas.seccion'].search([('name', '=', vals['name'])]):
            raise ValidationError('Ya existe una sección con este nombre. Por favor, elige un nombre diferente.')

        # Generar el código automáticamente si no está definido
        if vals.get('codigo', 'New') == 'New':
            vals['codigo'] = self.env['ir.sequence'].next_by_code('planillas.seccion') or 'New'
        return super(Seccion, self).create(vals)

    def write(self, vals):
        # Validar que no haya duplicados al editar
        if 'name' in vals:
            for record in self:
                if self.env['planillas.seccion'].search([('name', '=', vals['name']), ('id', '!=', record.id)]):
                    raise ValidationError(
                        'Ya existe una sección con este nombre. Por favor, elige un nombre diferente.')
        return super(Seccion, self).write(vals)

    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.codigo}] {record.name}" if record.codigo else record.name
            result.append((record.id, name))
        return result
