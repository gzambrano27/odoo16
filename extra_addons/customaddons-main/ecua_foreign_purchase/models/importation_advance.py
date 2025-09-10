from odoo.addons import decimal_precision as dp
import math
import time
import logging
from odoo import exceptions, _
from odoo import api, fields, models, _

READONLY_FIELD_STATES = {
    state: [('readonly', True)]
    for state in {'done'}
}


class ImportationAdvance(models.Model):
    _name = 'importation.advance'

    name = fields.Char(string="Nombre")
    date = fields.Date(string='Fecha', required=True, states=READONLY_FIELD_STATES, default=fields.Date.context_today)
    amount = fields.Float('Monto', required=True, states=READONLY_FIELD_STATES)
    account_id = fields.Many2one('account.account', 'Cuenta Origen', required=True, states=READONLY_FIELD_STATES)
    account_dest_id = fields.Many2one('account.account', 'Cuenta Destino', required=True, states=READONLY_FIELD_STATES)
    ref = fields.Char(string='Referencia', required=True, states=READONLY_FIELD_STATES)
    journal_id = fields.Many2one('account.journal', string="Diario", states=READONLY_FIELD_STATES)
    move_conciliation = fields.Many2one('account.move', 'Asiento Contable', readonly=True, store=True,
                                        tracking=True)
    partner_id = fields.Many2one('res.partner', string="Eempresa", states=READONLY_FIELD_STATES, tracking=True)
    state = fields.Selection([
        ('draft', 'BORRADOR'),
        ('done', 'REALIZADO')], 'Estado', readonly=True, tracking=True, default='draft')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('importation.trade') or ('New')
        result = super().create(vals_list)

        return result

    def confirmed_payment(self):
        for rec in self:
            move_lines = []
            move_lines.append((0, 0,
                               {'name': str(rec.account_id.name),
                                'debit': rec.amount,
                                'credit': 0,
                                'account_id': rec.account_id.id,
                                'date': rec.date,
                                # 'line_concilie_id': line.aml_ids.id,
                                'ref': str(rec.account_id.name),
                                # 'partner_id': self.partner_id.id
                                }))

            move_lines.append((0, 0,
                               {'name': str(rec.account_dest_id.name),
                                'debit': 0,
                                'credit': rec.amount,
                                'account_id': rec.account_dest_id.id,
                                'date': self.date,
                                # 'line_concilie_id': line.aml_ids.id,
                                'ref': str(rec.account_dest_id.name),
                                # 'partner_id': self.partner_id.id
                                }))

            line_data = {'date': rec.date,
                         'journal_id': rec.journal_id.id,
                         'state': 'draft',
                         'line_ids': move_lines,
                         'partner_id': self.partner_id.id or False,
                         'ref': "Conciliación: " + rec.ref}

            self.move_conciliation = self.env['account.move'].create(line_data)
            self.move_conciliation.action_post()
            self.write({'state': 'done'})

        return {'type': 'ir.actions.act_window_close'}
