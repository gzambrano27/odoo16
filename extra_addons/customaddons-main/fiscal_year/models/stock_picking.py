# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tools import format_datetime
from odoo.http import request
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager
import pytz
dateO = DateManager()
calendarO = CalendarManager()


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    period_id = fields.Many2one("account.fiscal.year", "Año Fiscal")
    period_line_id = fields.Many2one("account.fiscal.year.line", "Periodo Fiscal")

    @api.onchange( 'force_date')
    def onchange_force_date(self):
        for brw_each in self:
            brw_each.date_done=brw_each.force_date

    @api.constrains('date_done','force_date', 'state', 'company_id' )
    @api.onchange('date_done','force_date', 'state', 'company_id' )
    def validate_dates(self):
        OBJ_PERIOD_LINE = self.env["account.fiscal.year.line"].sudo()
        for brw_each in self:
            date = brw_each.date_done
            if brw_each.force_date:
                date =  brw_each.force_date
            if not date:
                date= fields.Datetime.now()

            tz_utc = pytz.timezone('UTC')
            tz_guayaquil = pytz.timezone('America/Guayaquil')

            date_utc = tz_utc.localize(date)  # Asegurar que la fecha está en UTC
            date = date_utc.astimezone(tz_guayaquil).date()

            brw_period,brw_period_line=  OBJ_PERIOD_LINE.get_periods(date, brw_each.company_id, for_stock_move_line=True)
            brw_each.period_id = brw_period and brw_period.id or False
            brw_each.period_line_id = brw_period_line and brw_period_line.id or False

    def _update_period_post_install(self,company_id):
        srch=self.env["stock.picking"].sudo().search([('state','!=','cancel'),
                                                      ('company_id','=',company_id),
                                                      '|',('period_line_id','=',False),('period_id','=',False)])
        for brw_each in srch:
            date = brw_each.date_done
            if brw_each.force_date:
                date = brw_each.force_date
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