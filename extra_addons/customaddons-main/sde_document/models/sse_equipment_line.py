# -*- coding: utf-8 -*-
from odoo import fields, models


class SseEquipmentLine(models.Model):
    _name = "sse.equipment.line"
    _description = "Línea de Equipo SSE"

    document_id = fields.Many2one(
        "sse.document", string="Documento", ondelete="cascade", required=True
    )

    modelo = fields.Char(string="Modelo", required=True)
    marca = fields.Char(string="Marca")
    serial_number = fields.Char(string="N.º Serie", required=True)
    color = fields.Char(string="Color")
