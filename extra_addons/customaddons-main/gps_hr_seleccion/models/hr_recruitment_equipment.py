from odoo import models, fields

class HrRecruitmentEquipment(models.Model):
    _name = "hr.recruitment.equipment"
    _description = "Equipos requeridos para el puesto"

    name = fields.Char(string="Equipo", required=True)
    quantity = fields.Integer(string="Cantidad", default=1)
    notes = fields.Text(string="Notas")
    applicant_id = fields.Many2one("hr.applicant", string="Solicitud de Empleo", ondelete="cascade")