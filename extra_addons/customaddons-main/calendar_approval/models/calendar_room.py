from odoo import models, fields

class CalendarRoom(models.Model):
    _name = 'calendar.room'
    _description = 'Salas para reuniones en el calendario'

    name = fields.Char('Nombre de la Sala', required=True)
    capacidad_minima = fields.Integer('Capacidad Mínima', required=True)
    capacidad_maxima = fields.Integer('Capacidad Máxima', required=True)

    responsible_id = fields.Many2one(
        'res.users',
        string='Responsable',
        help='Usuario encargado de aprobar las reservas en esta sala'
    )
