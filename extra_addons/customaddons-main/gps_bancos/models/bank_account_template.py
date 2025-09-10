# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
from ...message_dialog.tools import FileManager
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager

fileO = FileManager()
dateO = DateManager()
calendarO = CalendarManager()
from datetime import datetime, timedelta


class BankAccountTemplate(models.Model):
    _name = 'bank.account.template'
    _description = 'Plantilla para creación de Cuenta Bancaria'
    _inherit = ['mail.thread']  # opcional: para seguimiento

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('sent', 'Enviado'),
        ('done', 'Creado'),
    ], string='Estado', default='draft', tracking=True)

    acc_number = fields.Char('Número de Cuenta', required=True)
    acc_type = fields.Selection([
        ('iban', 'IBAN'),
        ('other', 'Otro'),
    ], string='Tipo', required=True)

    active = fields.Boolean('Activo', default=True)
    bank_id = fields.Many2one('res.bank', string='Banco', required=True)

    identificacion_tercero = fields.Char('Identificación del Tercero')
    l10n_latam_identification_tercero_id = fields.Many2one(
        'l10n_latam.identification.type', string='Tipo Identificación Tercero'
    )

    partner_id = fields.Many2one('res.partner', string='Tercero', required=True)

    partner_bank_id = fields.Many2one(
        'res.partner.bank', string='Cuenta Bancaria Generada', readonly=True, copy=False
    )

    # Opcional: puedes agregar comentarios, fecha de solicitud, etc.

    def action_send(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            rec.state = 'sent'

    def action_create_partner_bank(self):
        for rec in self:
            if rec.state != 'sent':
                raise ValidationError(_('Solo puedes crear la cuenta desde estado Enviado.'))
            bank_account = self.env['res.partner.bank'].create({
                'acc_number': rec.acc_number,
                'acc_type': rec.acc_type,
                'active': rec.active,
                'bank_id': rec.bank_id.id,
                'partner_id': rec.partner_id.id,
                'l10n_latam_identification_type_id': rec.l10n_latam_identification_tercero_id.id,
            })
            rec.partner_bank_id = bank_account.id
            rec.state = 'done'