# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tools import format_datetime
from odoo.http import request
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager

dateO = DateManager()
calendarO = CalendarManager()
import pytz
import logging

_logger = logging.getLogger(__name__)

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def write(self, vals):
        print('stock.move.linex',vals)
        return super(StockMoveLine , self).write(vals)

    period_id = fields.Many2one("account.fiscal.year", "Año Fiscal")
    period_line_id = fields.Many2one("account.fiscal.year.line", "Periodo Fiscal")

    @api.constrains('date', 'state', 'company_id','picking_id','qty_done' )
    @api.onchange('date', 'state', 'company_id','picking_id','qty_done' )
    def validate_dates(self):
        OBJ_PERIOD_LINE = self.env["account.fiscal.year.line"].sudo()
        for brw_each in self:
            date =  brw_each.date
            value=self._context.get('params',{})
            #print(self._context)
            #print(value)
            #print(brw_each)
            test_produccion=(("active_model" in value and value["active_model"]=='mrp.production') or
                             ("model" in value and value["model"]=='mrp.production') or (
                             ( not brw_each.picking_id and  ( brw_each.location_id.usage=='production' or
                                 brw_each.location_dest_id.usage == 'production'))
                             ))
            if not brw_each.picking_id or test_produccion:
                #print("not brw_each.picking_id or test_produccion",not brw_each.picking_id,test_produccion)
                #print(brw_each.picking_id)
                if test_produccion:
                    date=fields.Datetime.now()
                #print(date)
                tz_utc = pytz.timezone('UTC')
                tz_guayaquil = pytz.timezone('America/Guayaquil')
                date_utc = tz_utc.localize(date)  # Asegurar que la fecha está en UTC
                date = date_utc.astimezone(tz_guayaquil).date()
                brw_period,brw_period_line=  OBJ_PERIOD_LINE.get_periods(date, brw_each.company_id, for_stock_move_line=True)
                brw_each.period_id = brw_period and brw_period.id or False
                brw_each.period_line_id = brw_period_line and brw_period_line.id or False
            else:
                #print("en nevasdasasa")
                brw_period,brw_period_line=brw_each.picking_id.period_id,brw_each.picking_id.period_line_id
                brw_each.period_id = brw_period and brw_period.id or False
                brw_each.period_line_id = brw_period_line and brw_period_line.id or False

    def validate_reverse(self):
        for brw_each in self:
            if brw_each.period_id.state != "open":
                raise ValidationError(
                    _("Para modificar el estado de un movimiento de inventario el año fiscal %s para %s no debe estar 'en cierre' o 'cerrado' ") % (
                    brw_each.period_id.name, brw_each.period_id.company_id.name))
            if not (brw_each.period_line_id.state == "open" or (
                    brw_each.period_line_id.state == 'in_closing' and brw_each.period_line_id.for_stock_move_line)):
                raise ValidationError(
                    _("Para modificar el estado de un movimiento de inventario el periodo fiscal %s para %s no debe estar 'en cierre' o 'cerrado' ") % (
                    brw_each.period_line_id.name, brw_each.period_id.company_id.name))
        return True

    def unlink(self):
        return super(StockMoveLine, self).unlink()

    def _update_period_post_install(self, company_id):
        srch = self.env["stock.move.line"].sudo().search(
            [('state', '!=', 'cancel'), ('company_id', '=', company_id), '|', ('period_line_id', '=', False),
             ('period_id', '=', False)])
        for brw_each in srch:
            date = brw_each.date.date()#es datetime
            if date:
                self._cr.execute("""select fyl.id as period_line_id, fyl.state  
                from  account_fiscal_year fy
                inner join account_fiscal_year_line fyl on fyl.period_id=fy.id 
                where fy.company_id=%s   and %s>=fyl.date_from and %s<=fyl.date_to  """,
                                 (brw_each.company_id.id, date, date))
                result = self._cr.fetchall()
                if result:
                    brw_period_line = self.env["account.fiscal.year.line"].sudo().browse(result[0][0])
                    brw_each._write({"period_id": brw_period_line.period_id.id, "period_line_id": brw_period_line.id})
        return True
