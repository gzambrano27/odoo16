# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json

class CrmLeadScoringTemplate(models.Model):
    _name = "crm.lead.scoring.template"
    _description = "Plantilla de calificación de oportunidades"
    _order = "name"

    name = fields.Char(required=True)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company, index=True)
    line_ids = fields.One2many("crm.lead.scoring.template.line", "template_id", string="Preguntas")


class CrmLeadScoringTemplateLine(models.Model):
    _name = "crm.lead.scoring.template.line"
    _description = "Línea de plantilla de calificación"
    _order = "sequence, id"

    template_id = fields.Many2one("crm.lead.scoring.template", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    stage = fields.Char(string="Etapa/Grupo")
    description = fields.Char(required=True, string="Descripción")
    weight = fields.Float(string="Ponderación", digits=(16, 2), default=0.0)
    question_type = fields.Selection([
        ("yes_no", "Sí / No"),
        ("radio", "Opción única (radio)"),
    ], default="yes_no", required=True, string="Tipo de pregunta")
    group_key = fields.Char(
        string="Clave de grupo (radio)",
        help="Usa el mismo valor para opciones excluyentes de un mismo grupo."
    )


class CrmLeadScoringOption(models.Model):
    _name = "crm.lead.scoring.option"
    _description = "Opción de pregunta tipo radio"

    name = fields.Char(required=True)          # etiqueta visible en el dropdown
    weight = fields.Float(default=0.0)         # si quisieras pesos distintos por opción
    line_id = fields.Many2one("crm.lead.scoring.line", required=True, ondelete="cascade")

class CrmLeadScoringLine(models.Model):
    _name = "crm.lead.scoring.line"
    _description = "Respuesta de calificación en Lead"
    _order = "sequence, id"

    lead_id = fields.Many2one("crm.lead", required=True, ondelete="cascade")
    template_line_id = fields.Many2one("crm.lead.scoring.template.line", ondelete="set null")

    sequence = fields.Integer(default=10)
    stage = fields.Char(string="Etapa/Grupo")
    description = fields.Char(required=True, string="Descripción")
    weight = fields.Float(string="Ponderación", digits=(16, 2), default=0.0)
    question_type = fields.Selection([
        ("yes_no", "Sí / No"),
        ("radio", "Opción única (radio)"),
    ], default="yes_no", required=True, string="Tipo de pregunta")
    group_key = fields.Char(string="Grupo (radio)")

    answer_yes = fields.Boolean(string="Sí")     # para yes_no
    selected = fields.Boolean(string="Elegida")  # para radio

    points = fields.Float(string="Calificación", compute="_compute_points", store=True)

    radio_options_json = fields.Text(string="Opciones (JSON)")  # [{"key":"500_2","label":"Demanda entre 500kW a 2MW","weight":20}, ...]
    radio_choice = fields.Selection(selection=lambda self: self._radio_choices_dynamic(),
                                   string="Elegida")
    radio_choice_id = fields.Many2one("crm.lead.scoring.option", string="Opción elegida")
    option_ids = fields.One2many(
        "crm.lead.scoring.option",
        "line_id",
        string="Opciones"
    )

    @api.depends("answer_yes", "selected", "question_type", "weight", "radio_choice_id")
    def _compute_points(self):
        for line in self:
            if line.question_type == "yes_no":
                line.points = line.weight if line.answer_yes else 0.0
            elif line.question_type == "radio":
                # Puntaje fijo: si eligió alguna opción, vale 'weight' (ej. 20)
                line.points = line.weight if line.radio_choice_id else 0.0
            else:
                line.points = line.weight if line.selected else 0.0

    @api.model
    def _radio_choices_dynamic(self):
        """Devuelve un placeholder; la lista real se inyecta en onchange."""
        return []

    @api.onchange('radio_options_json')
    def _onchange_radio_options_json(self):
        """Cuando cargamos opciones, forzamos selección dinámica para el widget."""
        for rec in self:
            if rec.radio_options_json:
                opts = [(o['key'], o['label']) for o in json.loads(rec.radio_options_json)]
                # trucazo: asigna dinámicamente el selection
                type(rec).radio_choice.selection = opts

    @api.depends("answer_yes", "selected", "question_type", "weight", "radio_choice_id")
    def _compute_pointsOld(self):
        for line in self:
            if line.question_type == "yes_no":
                line.points = line.weight if line.answer_yes else 0.0
            elif line.question_type == "radio":
                # Si eligió alguna opción → cuenta el weight de la línea (20)
                #line.points = line.weight if line.radio_choice_id else 0.0
                line.points = line.radio_choice_id.weight if line.radio_choice_id else 0.0
            else:
                line.points = line.weight if line.selected else 0.0

    @api.depends("answer_yes", "selected", "question_type", "weight", "radio_choice_id")
    def _compute_points(self):
        for line in self:
            if line.question_type == "yes_no":
                line.points = line.weight if line.answer_yes else 0.0
            elif line.question_type == "radio":
                # Puntaje según la opción seleccionada
                line.points = line.radio_choice_id.weight if line.radio_choice_id else 0.0
            else:
                line.points = line.weight if line.selected else 0.0

    @api.onchange("selected")
    def _onchange_selected(self):
        for line in self:
            if line.question_type == "radio" and line.selected and line.group_key:
                siblings = line.lead_id.scoring_line_ids.filtered(
                    lambda l: l.id != line.id and l.question_type == "radio" and l.group_key == line.group_key
                )
                for sib in siblings:
                    sib.selected = False

    def write(self, vals):
        res = super().write(vals)
        if "selected" in vals and any(self.mapped("selected")):
            for line in self.filtered(lambda l: l.question_type == "radio" and l.selected and l.group_key):
                others = self.search([
                    ("lead_id", "=", line.lead_id.id),
                    ("question_type", "=", "radio"),
                    ("group_key", "=", line.group_key),
                    ("id", "!=", line.id),
                ])
                if others:
                    others.write({"selected": False})
        return res


class CrmLead(models.Model):
    _inherit = "crm.lead"

    scoring_template_id = fields.Many2one(
        "crm.lead.scoring.template", string="Plantilla de calificación",
        help="Plantilla de preguntas a usar en este lead."
    )
    scoring_line_ids = fields.One2many("crm.lead.scoring.line", "lead_id", string="Preguntas")
    score_total = fields.Float(string="Puntaje obtenido", compute="_compute_scores", store=True)
    score_max = fields.Float(string="Puntaje máximo", compute="_compute_scores", store=True)
    score_percent = fields.Float(string="%", compute="_compute_scores", store=True, group_operator="avg")

    @api.depends("scoring_line_ids.points", "scoring_line_ids.weight",
                 "scoring_line_ids.question_type", "scoring_line_ids.group_key")
    def _compute_scores(self):
        for lead in self:
            total = sum(lead.scoring_line_ids.mapped("points"))
            yes_no_weights = sum(lead.scoring_line_ids.filtered(lambda l: l.question_type == "yes_no").mapped("weight"))
            radio_groups = {}
            for l in lead.scoring_line_ids.filtered(lambda l: l.question_type == "radio"):
                key = l.group_key or f"grp_{l.id}"
                radio_groups[key] = max(radio_groups.get(key, 0.0), l.weight)
            max_score = yes_no_weights + sum(radio_groups.values())
            lead.score_total = total
            lead.score_max = max_score
            lead.score_percent = (total / max_score * 100.0) if max_score else 0.0
    
    def action_load_scoring_from_template(self):
        for lead in self:
            if not lead.scoring_template_id:
                raise ValidationError(_("Seleccione una plantilla de calificación."))

            # limpiar anteriores
            lead.scoring_line_ids.unlink()

            lines_cmds = []

            # 1) Preguntas Sí/No
            yes_no_tlines = lead.scoring_template_id.line_ids.filtered(lambda t: t.question_type == "yes_no")
            for tl in yes_no_tlines:
                lines_cmds.append((0, 0, {
                    "sequence": tl.sequence,
                    "stage": tl.stage,
                    "description": tl.description,
                    "weight": tl.weight,
                    "question_type": "yes_no",
                    "group_key": tl.group_key,
                    "template_line_id": tl.id,
                }))

            # 2) Preguntas Radio → colapsar en una sola línea con sus opciones
            radio_tlines = lead.scoring_template_id.line_ids.filtered(lambda t: t.question_type == "radio")
            groups = {}
            for tl in radio_tlines:
                key = tl.group_key or f"grp_{tl.id}"
                groups.setdefault(key, []).append(tl)

            for gkey, items in groups.items():
                items_sorted = sorted(items, key=lambda t: (t.sequence, t.id))

                # construyo opciones
                options_json = [
                    {"key": str(tl.id), "label": tl.description, "weight": tl.weight}
                    for tl in items_sorted
                ]

                parent = {
                    "sequence": items_sorted[0].sequence,
                    "stage": items_sorted[0].stage,
                    "description": "Consumo energético",  # o items_sorted[0].stage si quieres dinámico
                    "question_type": "radio",
                    "group_key": gkey,
                    "weight": 20.0,  # puntaje fijo por grupo
                    "option_ids": [
                            (0, 0, {"name": tl.description, "weight": tl.weight})
                            for tl in items_sorted
                        ],
                    "radio_options_json": json.dumps(options_json),  # 👈 clave para llenar el dropdown
                }
                lines_cmds.append((0, 0, parent))

            if lines_cmds:
                lead.write({"scoring_line_ids": lines_cmds})

        return True

    @api.onchange("scoring_template_id")
    def _onchange_scoring_template_id(self):
        for lead in self:
            if lead.scoring_template_id and not lead.scoring_line_ids:
                lead.action_load_scoring_from_template()
