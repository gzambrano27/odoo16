# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime


class AccountConfigurationPaymentBank(models.Model):
    _name = 'account.configuration.payment.bank'
    _description = "Configuraciones de Pagos al Banco"

    conf_payment_id = fields.Many2one(
        "account.configuration.payment",
        string="Configuracion de Pagos al Banco",
        ondelete="cascade",
        copy=False
    )
    bank_id=fields.Many2one('res.bank','Banco',required=True,domain=[('use_macro_format','=',True)])
    journal_ids=fields.Many2many('account.journal','account_conf_payment_bank_rel','conf_payment_id','journal_id','Diarios')



    _rec_name="bank_id"
