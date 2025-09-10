# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_

class AdvancePayment(models.TransientModel):
    _inherit="advance.payment"

    @api.model
    def _get_default_company_id(self):
        brw_purchase = self.env["purchase.order"].sudo().browse(self._context["active_id"])
        return brw_purchase.company_id.id

    company_id = fields.Many2one('res.company', "Compañía", default=_get_default_company_id)
    period_id = fields.Many2one("account.fiscal.year", "Año Fiscal")
    period_line_id = fields.Many2one("account.fiscal.year.line", "Periodo Fiscal")

    @api.constrains('date_planned',  'company_id')
    @api.onchange('date_planned',  'company_id')
    def validate_dates(self):
        OBJ_PERIOD_LINE = self.env["account.fiscal.year.line"].sudo()
        for brw_each in self:
            date = brw_each.date_planned.date()
            for_account_move = False
            for_stock_move_line = False
            for_account_payment = True
            brw_period, brw_period_line = OBJ_PERIOD_LINE.get_periods(date, brw_each.company_id,
                                                                      for_account_move=for_account_move,
                                                                      for_stock_move_line=for_stock_move_line,
                                                                      for_account_payment=for_account_payment)
            brw_each.period_id = brw_period and brw_period.id or False
            brw_each.period_line_id = brw_period_line and brw_period_line.id or False

    def get_payment(self, purchase_ids):
        vals = super().get_payment(purchase_ids)
        # Make sure the account move linked to generated payment
        # belongs to the expected sales team
        # team_id field on account.payment comes from the `_inherits` on account.move model
        vals.update({'period_id': self.period_id.id,
                     'period_line_id': self.period_line_id.id
                     })
        return vals


