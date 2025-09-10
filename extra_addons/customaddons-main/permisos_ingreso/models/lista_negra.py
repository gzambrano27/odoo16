# models/lista_negra.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ListaNegra(models.Model):
    _name = 'permisos_ingreso.lista_negra'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Lista Negra'

    # Campo calculado para almacenar el nombre completo de la persona, combinando apellidos y nombres
    name = fields.Char('Personal Name', compute='_compute_name', store=True)
    cedula = fields.Char(string='Cédula', required=True, tracking=True)
    apellidos = fields.Char(string='Apellidos', required=True, tracking=True)
    nombres = fields.Char(string='Nombres', required=True, tracking=True)

    # Metodo para calcular el campo 'name' concatenando los apellidos y nombres
    @api.depends('cedula','apellidos', 'nombres')
    def _compute_name(self):
        for record in self:
            # Combina los apellidos y nombres de la persona para formar el nombre completo
            record.name = f"{record.cedula} - {record.apellidos} {record.nombres}"

    @api.constrains('cedula')
    def _check_unique_cedula(self):
        for record in self:
            existing = self.search([('cedula', '=', record.cedula), ('id', '!=', record.id)])
            if existing:
                raise ValidationError('La cédula %s ya está registrada en la lista negra.' % record.cedula)

    @api.constrains('apellidos', 'nombres')
    def _check_unique_name(self):
        for record in self:
            existing = self.search([
                ('apellidos', '=', record.apellidos),
                ('nombres', '=', record.nombres),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError('El nombre %s %s ya está registrado en la lista negra.' % (record.apellidos, record.nombres))