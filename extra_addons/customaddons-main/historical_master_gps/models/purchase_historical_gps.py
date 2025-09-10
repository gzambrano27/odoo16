from odoo import models, fields

class PurchaseHistoricalGPS(models.Model):
    _name = 'purchase.historical.gps'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Historial de Compras GPS'

    name = fields.Char(string='Nombre', tracking=True)
    erp = fields.Char(string='ERP')
    categoria = fields.Char(string='Categoría')
    descripcion = fields.Text(string='Descripción')
    tipo_transaccion = fields.Char(string='Tipo de Transacción')
    tipo = fields.Char(string='Tipo')
    fecha = fields.Date(string='Fecha')
    nombre = fields.Char(string='Nombre')
    numero = fields.Char(string='Número')
    cantidad = fields.Float(string='Cantidad')
    costo = fields.Float(string='Costo')
    valor_1 = fields.Float(string='Valor 1')
    valor_2 = fields.Float(string='Valor 2')
    a_mano = fields.Float(string='A Mano')
    costo_promedio = fields.Float(string='Costo Promedio')
    valor_activo = fields.Float(string='Valor del Activo')
    costo_vta = fields.Float(string='Costo de Venta')
    mes = fields.Integer(string='Mes')
    anio = fields.Integer(string='Año')
    referencia_interna = fields.Char(string='Referencia Interna')
    proveedor = fields.Char(string='Proveedor')
    categoria_2 = fields.Char(string='Categoría 2')
    subcategoria = fields.Char(string='Subcategoría')
    marca = fields.Char(string='Marca')
