# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, date, time, timedelta
from odoo.exceptions import ValidationError

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
     
    ##is_transfer = fields.Boolean(default=False, string='Transferencia bancaria', help="Transferencia realizada")
    orden = fields.Char('Nro Orden')
    