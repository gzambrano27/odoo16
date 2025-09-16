from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountsAnalyticView(models.Model):
    _name = 'accounts.analytic.view'
    _description = 'Vista de Cuentas Analiticas'
    _auto = False

    id = fields.Integer(string="ID", readonly=True)

    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    company_name = fields.Char(string="Company Name", readonly=True)

    partner_id = fields.Many2one("res.partner", string="Partner", readonly=True)
    partner_name = fields.Char(string="Partner Name", readonly=True)


    nombre_proyecto = fields.Char(string="Nombre Proyecto", readonly=True)
    tipo_proyecto = fields.Char(string="Tipo Proyecto", readonly=True)
    ubicaciones = fields.Char(string="Ubicaciones", readonly=True)
    zona = fields.Char(string="Zona", readonly=True)
    estado = fields.Char(string="Estado", readonly=True)
    plan = fields.Char(string="Plan", readonly=True)
    codigo = fields.Char(string="Codigo", readonly=True)

    def init(self):
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW accounts_analytic_view AS (
                SELECT 
                    aa.id,
                    rc.id AS company_id,
                    rc.name AS company_name,
                    rp.id AS partner_id,
                    rp.name AS partner_name,
                    aa.name AS nombre_proyecto,
                    tp.name AS tipo_proyecto,
                    u.name AS ubicaciones,
                    z.name AS zona,
                    aa.state AS estado,
                    ap.name AS plan,
                    aa.code AS codigo
                FROM account_analytic_account aa
                INNER JOIN centro_costo_tipo_proyecto tp ON aa.tipo_proy_id = tp.id
                INNER JOIN centro_costo_ubicaciones u ON aa.ubicaciones_id = u.id
                INNER JOIN centro_costo_zona z ON aa.zona_id = z.id
                INNER JOIN account_analytic_plan ap ON aa.plan_id = ap.id
                LEFT JOIN res_partner rp ON aa.partner_id = rp.id
                INNER JOIN res_company rc ON aa.company_id = rc.id
            );
        """)

    _order="company_id asc, id desc"