# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from json import dumps

from odoo import _, api, fields, models

class CrmDivisionProyecto(models.Model):
    _name = 'crm.division.proyecto'
    _descripcion = 'Division de Proyecto'

    codigo = fields.Char('Codigo', size=3)
    name = fields.Char("Division",required=True,size=255)
    state=fields.Selection([('Activo', 'Activo'), ('Inactivo', 'Inactivo')], 'Estado')
    
    _order="name asc"


class CrmTipoProyecto(models.Model):
    _inherit = "centro.costo.tipo.proyecto"
    _description="Tipo Proyecto"
    
    division_id=fields.Many2one("crm.division.proyecto",'Division')    
    