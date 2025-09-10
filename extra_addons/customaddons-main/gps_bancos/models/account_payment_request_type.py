# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
from .import DEFAULT_MODE_PAYMENTS

class AccountPaymentRequestType(models.Model):
    _name = 'account.payment.request.type'
    _description = "Motivo de Solicitud"

    type=fields.Selection([('anulacion','Anulacion'),
                           ('registro','Registro')],string="Tipo",default="registro")
    code=fields.Char("Codigo",required=True,tracking=True)
    name = fields.Char("Descripcion ", required=True,tracking=True)
    active=fields.Boolean("Activo",default=True)

    default_mode_payment = fields.Selection(DEFAULT_MODE_PAYMENTS+[ ('*', 'Todos') ], string="Forma de Pago", default="*", tracking=True)

    # default_module = fields.Selection([('payslip', 'Nomina'),
    #                                          ('financial', 'Financiero'),
    #                                          ('*', 'Ambos')
    #                                          ], string="Modulo", default="financial", tracking=True)

    type_module = fields.Selection([('financial', 'Financiero'),
                                    ('payslip', 'Nómina'),
                                    ('*', 'Todos')], string="Tipo de Módulo", default="financial")

    _rec_name="name"
    _order="name asc"