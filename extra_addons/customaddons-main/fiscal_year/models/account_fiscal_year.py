# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager
dateO=DateManager()
calendarO=CalendarManager()

class AccountFiscalYear(models.Model):
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin','account.fiscal.year']
    _name="account.fiscal.year"
    _description = 'Año Fiscal'
    
    @api.model
    def _get_default_year(self):
        return fields.Date.today().year
    
    year=fields.Integer("Año",required=True,default=_get_default_year,tracking=True)
    name = fields.Char(string='Periodo',tracking=True)
    date_from = fields.Date(string='Fecha Inicial',tracking=True)
    date_to = fields.Date(string='Fecha Final',tracking=True)
    company_id = fields.Many2one('res.company', string='Compañia',tracking=True)
    line_ids=fields.One2many("account.fiscal.year.line","period_id","Periodos")
    state=fields.Selection([('draft','Preliminar'),('open','Abierto'),('closed','Cerrado')],
                           string="Estado",default="draft",required=True,tracking=True  )

    _check_company_auto = True


    @api.depends('year')
    @api.onchange('year')
    def onchange_year(self):
        self.name=str(self.year or self._get_default_year())
        self.date_from=date(self.year,1,1)
        self.date_to=date(self.year,12,31)
        line_ids=[(5,)]
        for month_val in range(1,13):
            brw_month=self.env["calendar.month"].sudo().search([('value','=',str(month_val) ) ])
            LAST_DAY=calendarO.days(self.year,month_val)
            line_ids.append((0,0,{
                "year":self.year,
                "month_id":brw_month.id,
                "name":"%s/%s" % (brw_month.name,self.year),
                "date_from":date(self.year,month_val,1),
                "date_to":date(self.year,month_val,LAST_DAY),
                "for_account_move":False,
                "for_stock_move_line":False
                }))    
        self.line_ids=line_ids
        
    def action_draft(self):
        for brw_each in self:
            if brw_each.state == 'open':
                if not self.env.user.has_group('fiscal_year.group_reapertura'):
                    raise ValidationError(_("No puedes usar esta accion contacta con un usuario habilitado!!"))
            for brw_line in brw_each.line_ids:
                if brw_line.state!="draft":
                    raise ValidationError(_("Solo puedes reversar el Año Fiscal si todos los periodos estan  en estado 'Preliminar' "))
            brw_each.write({"state":"draft"})
        return  True

    def action_closed(self):
        for brw_each in self:
            for brw_line in brw_each.line_ids:
                if brw_line.state!="closed":
                    raise ValidationError(_("Solo puedes cerrar el Año Fiscal si todos los periodos estan  en estado 'Cerrado' "))            
            brw_each.write({"state":"closed"})
        return  True
    
    def action_open(self):
        for brw_each in self:
            brw_each.write({"state":"open"})
        return  True


    