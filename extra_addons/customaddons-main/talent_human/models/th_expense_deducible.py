from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class YearDeducible(models.Model):
    _name = "year.deducible"
    _description = "Anios Deducibles"

    name = fields.Char('Name', required=True)
    sections = fields.One2many("gastos.deducibles.section" , 'aniodeducible','Anios Deducibles',copy = True)
    active = fields.Boolean(default=True)
    

class GastosDeducibles(models.Model):
    _name = "gastos.deducibles.section"
    _description = "Configuracion de gastos deducibles"

    aniodeducible = fields.Many2one("year.deducible", string="Anio", ondelete='cascade')
    tipo_gasto = fields.Many2one("tipo.gastos.deducibles", string="Gastos")
    valor = fields.Float(string="Valor",digits=(8,2))
    
class TipoGastosDeducibles(models.Model):
    _name = "tipo.gastos.deducibles"
    _description = 'Registro Maestro de Tipos de Gastos Deducibles'
    
    codigo = fields.Char("Codigo", size=3)
    name = fields.Char("Descripcion", size=1024)
    state = fields.Selection([('Activo','Activo'),('Inactivo','Inactivo')],    'Estado', default='Activo')
    

class RangoValores(models.Model):
    _name = "rango.valores"
    _description = "Rango Anios Deducibles"

    name = fields.Char('Name', required=True)
    line_ids = fields.One2many("rango.valores.line" , 'rangoid','Rangos',copy=True)
    active = fields.Boolean(default=True)
    
class RangoValoresLine(models.Model):
    _name = "rango.valores.line"
    _description = "Configuracion de rangos"

    rangoid = fields.Many2one("rango.valores", string="Rango", ondelete='cascade',copy = True)
    fraccion_basica = fields.Float(string="Faccion Basica",digits=(12,2),copy = True)
    exceso_hasta = fields.Float(string="Exceso Hasta",digits=(12,2),copy = True)
    impuesto_fraccion_basica = fields.Float(string="Imp Fraccion Basica",digits=(12,2),copy = True)
    porc_imp_fraccion_basica = fields.Integer(string="% Impuesto Fraccion Basica",copy = True)
    
class RangoValoresCargas(models.Model):
    _name = "rango.valores.cargas"
    _description = "Rango Valores Cargas Familiares"

    name = fields.Char('Name', required=True)
    line_ids = fields.One2many("rango.valores.cargas.line" , 'rangoid','Rangos',copy=True)
    active = fields.Boolean(default=True)
    
class RangoValoresCaargasLine(models.Model):
    _name = "rango.valores.cargas.line"
    _description = "Detalle Rango Valores Cargas Familiares"

    rangoid = fields.Many2one("rango.valores", string="Rango", ondelete='cascade',copy = True)
    num_cargas = fields.Integer(string="Numero Cargas",copy = True)
    num_canastas = fields.Integer(string="Numero Canastas",copy = True)
    gasto_deducible_maximo = fields.Float(string="Gasto Deducible Maximo",digits=(12,2),copy = True)
    rebaja_en_impuesto = fields.Float(string="Rebaja en el Impuesto",digits=(12,2),copy = True)
