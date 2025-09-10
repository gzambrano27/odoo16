# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class HrRegistrosReembolso(models.Model):
    _inherit = "hr.registro.reembolsos"

    def test_paid(self):
        DEC=2
        for brw_each in self:
            if brw_each.state=="approve":
                if round(brw_each.total_pagos_ant,DEC)==round(brw_each.total,DEC):
                    brw_each.write({"state":"paid"})
        return True
