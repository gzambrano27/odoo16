# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from json import dumps

from odoo import _, api, fields, models


class CrmLeadProject(models.Model):
    _name = "crm.lead.project"
    _description="Proyecto de Ventas"
    
    name=fields.Char("Proyecto",required=True,size=255)
    code=fields.Char("Código",required=True, copy=False, default="New", readonly=True)
    sequence_id=fields.Many2one("ir.sequence","Secuencia")
    
    _order="name asc"
    
    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Código debe ser único!')#,
        #('unique_name', 'UNIQUE(name)', 'Nombre debe ser único!')
    ]
    
    @api.model
    def create(self, vals):
        # 1) Generar el CÓDIGO del proyecto si no viene
        if not vals.get('code') or vals.get('code') in ('/', 'New'):
            vals['code'] = self.env['ir.sequence'].next_by_code('crm.lead.project.code') or '/'

        rec = super().create(vals)

        # 2) Crear la SECUENCIA por proyecto si no existe
        if not rec.sequence_id:
            # prefijo vacío: el prefijo visible lo ponemos al momento de armar el # Secuencial en el lead
            seq = self.env['ir.sequence'].create({
                'name': f"Secuencia - {rec.name} [{rec.code}]",
                'padding': 5,
                'number_next': 1,
                'implementation': 'no_gap',
                # 'code': f"crm.lead.project.seq.{rec.id}",  # opcional (no se usa si llamamos next_by_id)
            })
            rec.sequence_id = seq.id

        return rec
    
    