# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class HrEmployeeMovement(models.Model):
    _inherit = "hr.employee.movement"

    def action_reverse_payment_request(self):
        for brw_each in self:
            if brw_each.employee_payment_ids:
                brw_each.employee_payment_ids.action_draft()
                brw_each.employee_payment_ids.write({"state":"cancelled"})
                brw_each.write({
                    'employee_payment_ids': [(5,)]
                })
        return True