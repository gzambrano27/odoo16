# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager

dateO = DateManager()
calendarO = CalendarManager()


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    period_id = fields.Many2one("account.fiscal.year", "Año Fiscal")
    period_line_id = fields.Many2one("account.fiscal.year.line", "Periodo Fiscal")

    @api.constrains( 'date', 'state', 'company_id')
    @api.onchange( 'date', 'state', 'company_id')
    def validate_dates(self):
        OBJ_PERIOD_LINE = self.env["account.fiscal.year.line"].sudo()
        for brw_each in self:
            date = brw_each.date
            for_account_move = False
            for_stock_move_line = False
            for_account_payment = True
            brw_period, brw_period_line = OBJ_PERIOD_LINE.get_periods(date, brw_each.company_id,
                                                                      for_account_move=for_account_move,
                                                                      for_stock_move_line=for_stock_move_line,
                                                                      for_account_payment=for_account_payment)
            brw_each.period_id = brw_period and brw_period.id or False
            brw_each.period_line_id = brw_period_line and brw_period_line.id or False

    def validate_reverse(self):
        for brw_each in self:
            if brw_each.period_id.state!="open":
                raise ValidationError(_("Para modificar el estado de un pago/cobro el año fiscal %s para %s no debe estar 'en cierre' o 'cerrado' ") % (brw_each.period_id.name,brw_each.period_id.company_id.name))
            if not (brw_each.period_line_id.state=="open" or
                        (brw_each.period_line_id.state=='in_closing' and (
                                brw_each.period_line_id.for_account_payment
                        ))):
                raise ValidationError(_("Para modificar el estado de un pago/cobro el periodo fiscal %s para %s no debe estar 'en cierre' o 'cerrado' ") % (brw_each.period_line_id.name,brw_each.period_id.company_id.name) )
        return True

    def action_cancel(self):
        self.validate_reverse()
        values = None
        for brw_each in self:
            values = super(AccountPayment, brw_each).action_cancel()
        return values

    def action_post(self):
        self.validate_reverse()
        values=None
        for brw_each in self:
            values = super(AccountPayment, brw_each).action_post()
        return values

    def _update_period_post_install(self,company_id):
        srch=self.env["account.payment"].sudo().search([('state','!=','cancel'),('company_id','=',company_id),'|',('period_line_id','=',False),('period_id','=',False)])
        for brw_each in srch:
            date=brw_each.date
            if date:
                self._cr.execute("""select fyl.id as period_line_id, fyl.state  
                from  account_fiscal_year fy
                inner join account_fiscal_year_line fyl on fyl.period_id=fy.id 
                where fy.company_id=%s   and %s>=fyl.date_from and %s<=fyl.date_to  """, (brw_each.company_id.id, date, date))
                result = self._cr.fetchall()
                if result:
                    brw_period_line = self.env["account.fiscal.year.line"].sudo().browse(result[0][0])
                    brw_each._write({ "period_id":brw_period_line.period_id.id, "period_line_id":brw_period_line.id })
        return True