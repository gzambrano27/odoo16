# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    state_log_ids = fields.One2many(
        'purchase.request.state.log', 'request_id',
        string='Trazabilidad de estado', copy=False
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        log_vals = []
        now = fields.Datetime.now()
        uid = self.env.user.id

        for rec in records:
            # Evitar doble log si por algún motivo ya existe uno inicial
            if not rec.state_log_ids:
                log_vals.append({
                    'request_id': rec.id,
                    'state_from': False,
                    'state_to': rec.state or 'draft',
                    'note': _('Requisición creada'),
                    'changed_by': uid,
                    #'company_id': rec.company_id.id,
                    #'date': now,
                })
                try:
                    rec.message_post(body=_("Requisición creada. Estado inicial: <b>%s</b>") % (rec.state or '—'))
                except Exception:
                    pass

        if log_vals:
            self.env['purchase.request.state.log'].sudo().create(log_vals)
        return records

    def write(self, vals):
        # Si no cambia el estado, escribe normal
        if 'state' not in vals:
            return super().write(vals)

        # Guardar estado previo por registro
        pre_states = {rec.id: rec.state for rec in self}

        res = super().write(vals)

        now = fields.Datetime.now()
        uid = self.env.user.id
        log_vals = []

        for rec in self:
            old = pre_states.get(rec.id)
            new = rec.state
            if old != new:
                log_vals.append({
                    'request_id': rec.id,
                    'state_from': old,
                    'state_to': new,
                    'note': vals.get('note') or '',
                    'changed_by': uid,
                    #'company_id': rec.company_id.id,
                    #'date': now,
                })
                try:
                    rec.message_post(body=_("Estado cambiado de <b>%s</b> a <b>%s</b>.") % (old or '—', new or '—'))
                except Exception:
                    pass

        if log_vals:
            self.env['purchase.request.state.log'].sudo().create(log_vals)
        return res
