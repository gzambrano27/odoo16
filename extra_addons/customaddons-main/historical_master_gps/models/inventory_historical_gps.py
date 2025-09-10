from odoo import models, fields

class InventoryHistoricalGPS(models.Model):
    _name = 'inventory.historical.gps'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Historial de Inventario GPS'

    name = fields.Char(string='Nombre', tracking=True)
    sistema = fields.Char(string='Sistema')
    sku = fields.Char(string='SKU')
    mes1 = fields.Char(string='Mes')
    referencia_interna = fields.Char(string='Referencia Interna')
    nombre = fields.Char(string='Nombre')
    proveedor = fields.Char(string='Proveedor')
    categoria = fields.Char(string='Categoría')
    subcategoria = fields.Char(string='Subcategoría')
    marca = fields.Char(string='Marca')
    costo = fields.Float(string='Costo')
    cantidad_a_mano = fields.Float(string='Cantidad a Mano')
    stock_virtual = fields.Float(string='Stock Virtual')
    costo_total = fields.Float(string='Costo Total')
    mes2 = fields.Integer(string='Número de mes')
    anio = fields.Char(string='Año')
