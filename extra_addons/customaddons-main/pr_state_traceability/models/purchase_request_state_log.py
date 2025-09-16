# -*- coding: utf-8 -*-
from odoo import models, fields

STATE_SELECTION = [
    ('draft', 'Borrador'),
    ('to_approve', 'Para aprobar'),
    ('approved', 'Aprobado'),
    ('in_progress', 'En progreso'),
    ('done', 'Realizado'),
    ('rejected', 'Rechazado'),
]

class PurchaseRequestStateLog(models.Model):
    _name = 'purchase.request.state.log'
    _description = 'Trazabilidad de Estados de PR'
    _order = 'changed_on desc, id desc'

    request_id = fields.Many2one('purchase.request', string='Requisicion de compra', required=True, index=True, ondelete='cascade')
    state_from = fields.Selection(STATE_SELECTION, string='De', required=False)
    state_to = fields.Selection(STATE_SELECTION, string='A', required=True)
    changed_by = fields.Many2one('res.users', string='Cambiado por', default=lambda self: self.env.user, readonly=True)
    changed_on = fields.Datetime(string='Fecha/Hora', default=fields.Datetime.now, readonly=True)
    note = fields.Char(string='Nota')
    company_id = fields.Many2one(
        'res.company', related='request_id.company_id',
        store=True, index=True, readonly=True
    )
