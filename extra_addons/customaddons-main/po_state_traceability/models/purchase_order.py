# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    state_log_ids = fields.One2many('purchase.order.state.log', 'order_id', string='Trazabilidad de estado')

    def write(self, vals):
        pre_states = {}
        if 'state' in vals:
            for rec in self:
                pre_states[rec.id] = rec.state

        res = super().write(vals)

        if 'state' in vals:
            logs = []
            for rec in self:
                old = pre_states.get(rec.id)
                new = rec.state
                if old != new:
                    logs.append({
                        'order_id': rec.id,
                        'state_from': old,
                        'state_to': new,
                        'note': vals.get('note') or '',
                        'changed_by': self.env.user.id,
                    })
                    rec.message_post(body=f"Estado cambiado de <b>{old or '—'}</b> a <b>{new}</b>.")
            if logs:
                self.env['purchase.order.state.log'].create(logs)
        return res

    @api.model
    def create(self, vals):
        po = super().create(vals)
        # Primer registro de trazabilidad: creación de la OC
        self.env['purchase.order.state.log'].sudo().create({
            'order_id': po.id,
            #'date': po.create_date or fields.Datetime.now(),
            #'user_id': po.create_uid.id if po.create_uid else self.env.user.id,
            'state_from':po.purchase_request_id.name or '',
            'changed_by': self.env.user.id,
            'state_from': False,
            'state_to': 'draft',  # ajusta si tu selección usa otro valor para “borrador”
            'note': "Orden de compra creada desde %s" % (po.purchase_request_id.display_name if po.purchase_request_id else ""),
        })
        return po