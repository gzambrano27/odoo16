# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from json import dumps

from odoo import _, api, fields, models


class CrmLeadProject(models.Model):
    _name = "crm.lead.project"
    _description="Proyecto de Ventas"
    
    name=fields.Char("Proyecto",required=True,size=255)
    code=fields.Char("Código",required=True,size=10)
    sequence_id=fields.Many2one("ir.sequence","Secuencia")
    
    _order="name asc"
    
    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Código debe ser único!')#,
        #('unique_name', 'UNIQUE(name)', 'Nombre debe ser único!')
    ]
    
    @api.model 
    def create(self, vals):
        if 'sequence_id' not in vals:
            brw_sequence=self.env['ir.sequence'].create({"name":vals["name"],"code":vals["code"],"padding":5,"number_next":1})
            vals['sequence_id'] = brw_sequence.id
        return super(CrmLeadProject, self).create(vals)
    
    