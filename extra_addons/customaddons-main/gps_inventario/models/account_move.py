# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from odoo.exceptions import ValidationError,UserError
from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit="account.move"
    