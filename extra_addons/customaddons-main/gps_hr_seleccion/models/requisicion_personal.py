from odoo import models, fields, api, _
from odoo.exceptions import UserError

class RequisicionPersonal(models.Model):
    _name = "requisicion.personal"
    _description = "Requisición de Personal"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = "id desc"

    name = fields.Char(
        string="Número",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('requisicion.personal')
    )
    fecha_solicitud = fields.Date("Fecha de Solicitud", default=fields.Date.today, tracking=True)
    departamento_id = fields.Many2one("hr.department", string="Departamento", required=True, tracking=True)
    puesto = fields.Char("Puesto requerido", required=True, tracking=True)
    cantidad = fields.Integer("Cantidad", required=True, default=1, tracking=True)
    motivo = fields.Text("Motivo de la requisición")

    solicitante_id = fields.Many2one("res.users", string="Solicitante", default=lambda self: self.env.user, tracking=True, readonly=True)
    state = fields.Selection([
        ("draft", "Borrador"),
        ("en_revision", "En Revisión (Jefe)"),
        ("aprobacion_gerente", "En Aprobación (Gerente)"),
        ("aprobado", "Aprobado"),
        ("rechazado", "Rechazado"),
    ], string="Estado", default="draft", tracking=True, copy=False)

    # --- TRANSICIONES ---
    def _check_group(self, xml_id):
        if not self.env.user.has_group(xml_id):
            raise UserError(_("No tienes permisos para esta acción."))

    def action_enviar_revision(self):
        # Usuario puede enviar a revisión
        self._check_group("requisicion_personal.group_requisicion_personal_usuario")
        self.write({"state": "en_revision"})

    def action_aprobar_jefe(self):
        # Solo Jefe
        self._check_group("requisicion_personal.group_requisicion_personal_jefe")
        self.write({"state": "aprobacion_gerente"})

    def action_aprobar_gerente(self):
        # Solo Gerente
        self._check_group("requisicion_personal.group_requisicion_personal_gerente")
        self.write({"state": "aprobado"})

    def action_rechazar(self):
        # Jefe o Gerente pueden rechazar
        if not (self.env.user.has_group("requisicion_personal.group_requisicion_personal_jefe") or
                self.env.user.has_group("requisicion_personal.group_requisicion_personal_gerente") or
                self.env.user.has_group("requisicion_personal.group_requisicion_personal_admin")):
            raise UserError(_("No tienes permisos para rechazar."))
        self.write({"state": "rechazado"})
