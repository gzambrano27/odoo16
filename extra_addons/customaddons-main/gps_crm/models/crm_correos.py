# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from json import dumps

from odoo import _, api, fields, models


class CrmCorreo(models.Model):
    _name = "crm.correo"
    _description="Proyecto de Ventas"
    
    name=fields.Char("Correo",required=True,size=255)
    tipo=fields.Selection([('Financiamiento', 'Financiamiento'), ('Visita', 'Visita Tecnica')], 'Tipo')
    correo=fields.Char("Correo")
    description = fields.Html(string="Mensaje")
    estado=fields.Selection([('Activo', 'Activo'), ('Inactivo', 'Inactivo')], 'Estado')
    
    _order="name asc"
    
    