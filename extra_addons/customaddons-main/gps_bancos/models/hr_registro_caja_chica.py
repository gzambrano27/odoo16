# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class HrRegistroCajaChica(models.Model):
    _inherit = "hr.registro.caja.chica"

    def test_paid(self):
        DEC=2
        for brw_each in self:
            if brw_each.state=="approve":
                if round(brw_each.total,DEC)==round(brw_each.val_pagado,DEC):
                    brw_each.write({"state":"paid"})
        return True