from odoo import models, fields

class SalaReunion(models.Model):
    _name = 'sala.reunion'
    _description = 'Sala de Reuniones'

    name = fields.Char(string='Nombre de la Sala', required=True)
    capacidad = fields.Integer(string='Capacidad', required=True)
    descripcion = fields.Text(string='Descripción')