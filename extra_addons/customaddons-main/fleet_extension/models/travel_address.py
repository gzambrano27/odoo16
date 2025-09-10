from odoo import models, fields, api

class TravelAddress(models.Model):
    _name = 'travel.address'
    _description = 'Direcciones de Viaje'

    name = fields.Char(string="Nro Direcciones", required=True)
    place = fields.Char(string="Lugar", required=True)
