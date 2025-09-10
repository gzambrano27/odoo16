from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Categoria(models.Model):
    _name = 'planillas.categoria'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Categoría'

    name = fields.Char(string='Nombre', tracking=True)
    codigo = fields.Char(string='Código', copy=False, default=lambda self: 'New')
    estado = fields.Selection([
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo')
    ], string='Estado', default='activo', tracking=True)
    seccion_id = fields.Many2one('planillas.seccion', string='Sección', tracking=True, domain=[('estado', '=', 'activo')])

    @api.model
    def create(self, vals):
        # Validar duplicados en la combinación de 'name' y 'seccion_id'
        if 'name' in vals and 'seccion_id' in vals:
            if self.env['planillas.categoria'].search([
                ('name', '=', vals['name']),
                ('seccion_id', '=', vals['seccion_id'])
            ]):
                raise ValidationError('Ya existe una categoría con este nombre en la misma sección. Por favor, elige un nombre diferente.')

        # Generar código automáticamente si no está definido
        if vals.get('codigo', 'New') == 'New':
            vals['codigo'] = self.env['ir.sequence'].next_by_code('planillas.categoria') or 'New'
        return super(Categoria, self).create(vals)

    def write(self, vals):
        # Validar duplicados en la combinación de 'name' y 'seccion_id' al editar
        for record in self:
            new_name = vals.get('name', record.name)
            new_seccion_id = vals.get('seccion_id', record.seccion_id.id)
            if self.env['planillas.categoria'].search([
                ('name', '=', new_name),
                ('seccion_id', '=', new_seccion_id),
                ('id', '!=', record.id)
            ]):
                raise ValidationError('Ya existe una categoría con este nombre en la misma sección. Por favor, elige un nombre diferente.')
        return super(Categoria, self).write(vals)

    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.codigo}] {record.name}" if record.codigo else record.name
            result.append((record.id, name))
        return result
