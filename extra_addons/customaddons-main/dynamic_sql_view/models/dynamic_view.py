from odoo import models, fields, api
from odoo.exceptions import ValidationError

class DynamicSQLView(models.Model):
    _name = "dynamic.sql.view"
    _description = "Vistas SQL dinámicas para Power BI"

    name = fields.Char("Nombre de la vista", required=True)
    sql_query = fields.Text("Consulta SQL (solo SELECT)", required=True)
    state = fields.Selection([
        ("draft", "Borrador"),
        ("created", "Vista Creada")
    ], default="draft")
    created_by = fields.Many2one("res.users", string="Creado por", default=lambda self: self.env.user)
    created_at = fields.Datetime("Fecha de creación", default=fields.Datetime.now)
    last_updated = fields.Datetime("Última actualización")

    @api.constrains("sql_query")
    def _check_sql(self):
        forbidden = ["drop", "delete", "insert", "update", "alter", "truncate"]
        for record in self:
            sql = record.sql_query.strip().lower()
            if not sql.startswith("select"):
                raise ValidationError("Solo se permiten consultas que empiecen con SELECT.")
            if any(word in sql for word in forbidden):
                raise ValidationError("La consulta contiene comandos no permitidos.")

    def action_create_view(self):
        for record in self:
            view_name = "usr_" + record.name.lower().replace(" ", "_")
            query = f"CREATE OR REPLACE VIEW {view_name} AS {record.sql_query}"
            try:
                self.env.cr.execute(query)
                record.state = "created"
                record.last_updated = fields.Datetime.now()
            except Exception as e:
                raise ValidationError(f"Error al crear la vista: {e}")
