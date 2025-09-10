from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Proyecto(models.Model):
    # Nombre técnico del modelo en Odoo
    _name = 'permisos_ingreso.proyecto'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    # Descripción del modelo que aparecerá en la interfaz de Odoo
    _description = 'Proyecto'
    # Campo calculado que almacena el nombre del proyecto, basado en el campo 'nombre'
    name = fields.Char('Proyecto Name', compute='_compute_name', store=True)
    # Campo de texto para almacenar el nombre del proyecto, obligatorio
    nombre = fields.Char(string='Nombre del Proyecto', required=True, tracking = True)
    # Campo de texto para almacenar la ubicación del proyecto, obligatorio
    ubicacion = fields.Char(string='Ubicación', required=True, tracking = True)

    # Metodo para calcular el campo 'name' basado en el valor del campo 'nombre'
    @api.depends('nombre','ubicacion')
    def _compute_name(self):
        for record in self:
            record.name =  f"{record.nombre}/{record.ubicacion}"

    # Metodo para validar que la combinación de nombre y ubicación no se repita
    @api.constrains('nombre','ubicacion')
    def _check_unique_name_ubicacion(self):
        for record in self:
            # Buscar registros con la misma combinación de nombre y ubicación (excluyendo el registro actual)
            if self.search_count([('nombre', '=', record.nombre), ('ubicacion', '=', record.ubicacion), ('id', '!=', record.id)]) > 0:
                raise ValidationError(f'La combinación de nombre "{record.nombre}" y ubicación "{record.ubicacion}" ya existe en otro proyecto.')
