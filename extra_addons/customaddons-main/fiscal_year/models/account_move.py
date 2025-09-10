# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager
dateO=DateManager()
calendarO=CalendarManager()

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    #@api.model
    #def _get_default_invoice_date(self):
    #    return fields.Date.today()
    
    #invoice_date=fields.Date(default=_get_default_invoice_date)
    period_id=fields.Many2one("account.fiscal.year","Año Fiscal")
    period_line_id=fields.Many2one("account.fiscal.year.line","Periodo Fiscal")
    from_stock_move_line=fields.Boolean("Desde Mov. de Inventarios",compute="_get_compute_from_stock_move_line")

    def _get_compute_from_stock_move_line(self):
        for brw_each in self:
            from_stock_move_line=False
            srch=self.env["stock.valuation.layer"].sudo().search([('account_move_id','=',brw_each.id)])
            if srch:
                from_stock_move_line=True
            brw_each.from_stock_move_line=from_stock_move_line

    @api.constrains('move_type','invoice_date','date','state','company_id','payment_id')
    @api.onchange('move_type','invoice_date','date','state','company_id','payment_id')
    def validate_dates(self):
        OBJ_PERIOD_LINE=self.env["account.fiscal.year.line"].sudo()
        for brw_each in self:
            date=brw_each.date
            if brw_each.move_type!= "entry":
                date=brw_each.invoice_date or brw_each.date
            for_account_move=True
            for_stock_move_line=False
            for_account_payment = False
            if brw_each.stock_move_id:
                for_account_move =False
                for_stock_move_line=True
                for_account_payment=False
            if brw_each.payment_id or self._context.get('is_payment',False):
                for_account_move =False
                for_stock_move_line=False
                for_account_payment=True
            brw_period,brw_period_line=OBJ_PERIOD_LINE.get_periods(date,brw_each.company_id,
                                                                    for_account_move=for_account_move,
                                                                    for_stock_move_line=for_stock_move_line,
                                                                    for_account_payment=for_account_payment)
            brw_each.period_id=brw_period and brw_period.id or False
            brw_each.period_line_id=brw_period_line and brw_period_line.id or False
    
    def validate_reverse(self):
        for brw_each in self:
            if brw_each.period_id.state!="open":                
                raise ValidationError(_("Para modificar el estado de un documento contable el año fiscal %s para %s no debe estar 'en cierre' o 'cerrado' ") % (brw_each.period_id.name,brw_each.period_id.company_id.name))
            if not (brw_each.period_line_id.state=="open" or
                        (brw_each.period_line_id.state=='in_closing' and (
                                ( (brw_each.period_line_id.for_account_move and (not brw_each.stock_move_id and not brw_each.payment_id)) or
                                  (brw_each.period_line_id.for_account_payment and brw_each.payment_id) or
                                  (brw_each.period_line_id.for_stock_move_line and brw_each.stock_move_id)
                                )
                        ))):
                dscr="Documento Contable"
                if brw_each.period_line_id.for_account_payment and brw_each.payment_id:
                    dscr = "Pago/Cobro"
                if brw_each.period_line_id.for_stock_move_line and brw_each.stock_move_id:
                    dscr = "Movimiento de Inventario"
                raise ValidationError(_("Para modificar el estado de un %s el periodo fiscal %s para %s no debe estar 'en cierre' o 'cerrado' ") % (dscr,brw_each.period_line_id.name,brw_each.period_id.company_id.name) )
        return True



    def _post(self, soft=True):
        for brw_each in self:
            brw_each.validate_reverse()
        return super(AccountMove,self)._post(soft=soft)

    def button_draft(self):
        for brw_each in self:
            brw_each.validate_reverse()
        return super(AccountMove,self).button_draft()
    
    def button_cancel(self):
        for brw_each in self:
            brw_each.validate_reverse()
        return super(AccountMove,self).button_cancel()

    def unlink(self):
        for brw_each in self:
            if brw_each.state!='draft':
                brw_each.validate_reverse()
        return super(AccountMove,self).unlink()

    def _update_period_post_install(self,company_id):
        srch=self.env["account.move"].sudo().search([('state','!=','cancel'),('company_id','=',company_id),'|',('period_line_id','=',False),('period_id','=',False)])
        for brw_each in srch:
            date=brw_each.date
            if brw_each.move_type!= "entry":
                date=brw_each.invoice_date
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
    