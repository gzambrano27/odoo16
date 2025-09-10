# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from json import dumps

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    lead_project_id=fields.Many2one("crm.lead.project","Proyecto de Venta")
    lead_project_sequence=fields.Char("# Secuencial")
   
        