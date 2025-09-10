from odoo import models, fields

class SaleHistoricalGPS(models.Model):
    _name = 'sale.historical.gps'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Historial de Ventas GPS'

    name = fields.Char(string='Nombre', tracking=True)
    sistema = fields.Char(string='Sistema')
    referencia_interna = fields.Char(string='Referencia Interna')
    categoria = fields.Char(string='Categoría')
    descripcion = fields.Text(string='Descripción')
    tipo = fields.Char(string='Tipo')
    fecha = fields.Date(string='Fecha')
    mes = fields.Integer(string='Mes')
    anio = fields.Integer(string='Año')
    numero = fields.Char(string='Número')
    memoria = fields.Text(string='Memoria')
    nombre = fields.Char(string='Nombre')
    cantidad = fields.Float(string='Cantidad')
    costo = fields.Float(string='Costo')
    pvp = fields.Float(string='PVP')  # Precio de venta al público
    categoria_2 = fields.Char(string='Categoría 2')
    subcategoria = fields.Char(string='Subcategoría')
