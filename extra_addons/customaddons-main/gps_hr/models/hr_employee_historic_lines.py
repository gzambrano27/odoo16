# -- coding: utf-8 --
# -- encoding: utf-8 --
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
import base64

from ...calendar_days.tools import CalendarManager, DateManager, MonthManager

dtObj = DateManager()
caObj = CalendarManager()



class HrEmployeeHistoricLines(models.Model):
    _name = "hr.employee.historic.lines"
    _description = "Historicos de los Empleados"

    payslip_line_id=fields.Many2one("hr.payslip.line","Linea de Nomina",ondelete="cascade")
    company_id=fields.Many2one("res.company","Empresa",required=True,copy=False,
        default=lambda self: self.env.company,)

    currency_id = fields.Many2one(related="company_id.currency_id",store=False,readonly=True )

    employee_id = fields.Many2one("hr.employee", "Empleado", required=True)
    payslip_id = fields.Many2one("hr.payslip", "Rol", required=False)

    name=fields.Char("Periodo",required=False,compute="_get_dates",store=True,readonly=True)
    grouped=fields.Boolean("Agrupado",default=False)
    month_id=fields.Many2one("calendar.month",required=False,string="Mes")
    year = fields.Integer( required=False, string="Anio")
    date_from=fields.Date(string="Fecha Inicio",compute="_get_dates",store=True,readonly=True)
    date_to = fields.Date(string="Fecha Fin",compute="_get_dates",store=True,readonly=True)
    amount=fields.Monetary("Monto",required=True)
    rule_id=fields.Many2one("hr.salary.rule","Rubro",required=True)
    amount_to_paid = fields.Monetary("A pagar", required=True,default=0.00,compute="_get_amounts",store=True,readonly=True)
    amount_paid = fields.Monetary("Pagado", required=True,default=0.00,compute="_get_amounts",store=True,readonly=True)
    amount_residual = fields.Monetary("Pendiente", required=True,default=0.00,compute="_get_amounts",store=True,readonly=True)
    state=fields.Selection([('draft','Preliminar'),
                            ('posted','Publicado'),
                            ('liquidated','Liquidado')
                            ],string="Estado",required=True,default="draft")

    movement_line_id =fields.Many2one("hr.employee.movement.line","Linea de Movimiento de Empleado")


    @api.onchange('grouped')
    def onchange_grouped(self):
        self.month_id=False

    def unlink(self):
        if any(brw_each.state != 'draft' for brw_each in self):
            raise ValidationError(_("No puedes borrar un registro que no sea preliminar"))
        values = super(HrEmployeeHistoricLines, self).unlink()
        return values

    @api.onchange('grouped','month_id','year')
    @api.depends('grouped', 'month_id', 'year')
    def _get_dates(self):
        for brw_each in self:
            if not brw_each.grouped:
                if brw_each.year and  brw_each.month_id:
                    brw_each.date_from = dtObj.create(brw_each.year, brw_each.month_id.value, 1)
                    brw_each.date_to = dtObj.create(brw_each.year, brw_each.month_id.value, caObj.days(brw_each.year, brw_each.month_id.value))
                    brw_each.name = "PERIODO %s DEL %s" % ( brw_each.month_id.name.upper(),brw_each.year)
                else:
                    brw_each.date_from = None
                    brw_each.date_to = None
                    brw_each.name = "PERIODO ..."
            else:
                if brw_each.year:
                    brw_each.date_from = dtObj.create(brw_each.year, 1, 1)
                    brw_each.date_to = dtObj.create(brw_each.year,12,31)
                    brw_each.name="PERIODO %s" % (brw_each.year,)
                else:
                    brw_each.date_from = None
                    brw_each.date_to = None
                    brw_each.name = "PERIODO ..."

    @api.onchange('state', 'amount','payslip_line_id')
    @api.depends('state', 'amount','payslip_line_id')
    def _get_amounts(self):
        DEC=2
        for brw_each in self:
            if brw_each.state=="draft":
                brw_each.amount_to_paid=0.00
                brw_each.amount_paid = 0.00
                brw_each.amount_residual = 0.00
            else:
                brw_each.amount_to_paid = brw_each.amount
                amount_paid=0.00
                if brw_each.state=='liquidated':
                    amount_paid=brw_each.amount
                brw_each.amount_paid = amount_paid
                brw_each.amount_residual =round(brw_each.amount_to_paid-amount_paid,DEC)

    def action_posted(self):
        for brw_each in self:
            brw_each.write({"state":"posted"})
        return True

    def action_draft(self):
        for brw_each in self:
            brw_each.write({"state":"draft"})
        return True