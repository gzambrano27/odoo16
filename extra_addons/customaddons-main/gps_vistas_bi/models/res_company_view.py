from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResCompanyView(models.Model):
    _name = 'res.company.view'
    _description = 'Vista de Empresas Relacionadas'
    _auto = False

    id = fields.Integer(string="ID", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Company", readonly=True)
    partner_name = fields.Char(string="Company Name", readonly=True)

    def init(self):
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW res_company_view AS (
              
              select rc.id,
	rc.id as partner_id,
	rc.name as company_name

from res_company rc
inner join res_partner rp on rp.id=rc.partner_id

)
        """)

    _order="id asc"