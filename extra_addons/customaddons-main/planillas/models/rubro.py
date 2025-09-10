from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Rubro(models.Model):
    _name = 'planillas.rubro'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Rubro'

    name = fields.Char(string='Nombre', tracking=True)
    codigo = fields.Char(string='Código', copy=False, default=lambda self: 'New')
    estado = fields.Selection([
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo')
    ], string='Estado', default='activo', tracking=True)
    categoria_id = fields.Many2one('planillas.categoria', string='Categoría', tracking=True, domain=[('estado', '=', 'activo')])

    unidad_medida = fields.Many2one('uom.uom', string='Unidad de Medida', tracking=True,
                                    help="Unidad de medida asociada al rubro (ej. kg, m, etc.)")

    precio_unitario = fields.Float(string='Precio Unitario', tracking=True,
                                   help="Precio unitario del rubro", default=0.0)

    @api.constrains('precio_unitario', 'descuento')
    def _check_numeric_values(self):
        for record in self:
            if record.precio_unitario < 0:
                raise ValidationError("El precio unitario no puede ser negativo.")

    @api.model
    def create(self, vals):
        # Validar duplicados en la combinación de 'name' y 'categoria_id'
        if 'name' in vals and 'categoria_id' in vals:
            if self.env['planillas.rubro'].search([
                ('name', '=', vals['name']),
                ('categoria_id', '=', vals['categoria_id'])
            ]):
                raise ValidationError(
                    'Ya existe un rubro con este nombre en la misma categoría. Por favor, elige un nombre diferente.')

        # Generar código automáticamente si no está definido
        if vals.get('codigo', 'New') == 'New':
            vals['codigo'] = self.env['ir.sequence'].next_by_code('planillas.rubro') or 'New'
        return super(Rubro, self).create(vals)

    def write(self, vals):
        # Validar duplicados en la combinación de 'name' y 'categoria_id' al editar
        for record in self:
            new_name = vals.get('name', record.name)
            new_categoria_id = vals.get('categoria_id', record.categoria_id.id)
            if self.env['planillas.rubro'].search([
                ('name', '=', new_name),
                ('categoria_id', '=', new_categoria_id),
                ('id', '!=', record.id)
            ]):
                raise ValidationError(
                    'Ya existe un rubro con este nombre en la misma categoría. Por favor, elige un nombre diferente.')
        return super(Rubro, self).write(vals)

    def name_get(self):
        result = []
        for rubro in self:
            name = f"[{rubro.codigo}] {rubro.name}" if rubro.codigo else rubro.name
            result.append((rubro.id, name))
        return result