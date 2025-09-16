# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
import re

class ResCompany(models.Model):
    _inherit="res.company"

    def create(self, vals):
        self = self.with_context(bypass_partner_restriction=True)
        return super(ResCompany,self)   .create(vals)
