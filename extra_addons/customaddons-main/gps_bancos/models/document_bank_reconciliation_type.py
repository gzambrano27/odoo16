# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID


class DocumentBankReconciliationType(models.Model):
    _name = "document.bank.reconciliation.type"
    _description = "Tipo de Documento de Reconciliacion"

    code=fields.Char("Codigo",required=True)
    name = fields.Char("Nombre", required=True)
    descriptions = fields.Char("Descripciones", required=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'El código debe ser único.'),
    ]
