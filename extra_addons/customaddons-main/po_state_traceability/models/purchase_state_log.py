# -*- coding: utf-8 -*-
from odoo import models, fields

STATE_SELECTION = [
    ('draft', 'SdP'),
    ('control_presupuesto', 'Control Presupuesto'),
    ('sent', 'SDP Enviada'),
    ('to approve', 'Para aprobar'),
    ('purchase', 'Orden de compra'),
    ('done', 'Bloqueada'),
    ('cancel', 'Cancelado'),
]

class PurchaseOrderStateLog(models.Model):
    _name = 'purchase.order.state.log'
    _description = 'Trazabilidad de Estados de OC'
    _order = 'changed_on desc, id desc'

    order_id = fields.Many2one('purchase.order', string='Orden de compra', required=True, index=True, ondelete='cascade')
    state_from = fields.Selection(STATE_SELECTION, string='De', required=False)
    state_to = fields.Selection(STATE_SELECTION, string='A', required=True)
    changed_by = fields.Many2one('res.users', string='Cambiado por', default=lambda self: self.env.user, readonly=True)
    changed_on = fields.Datetime(string='Fecha/Hora', default=fields.Datetime.now, readonly=True)
    note = fields.Char(string='Nota')
