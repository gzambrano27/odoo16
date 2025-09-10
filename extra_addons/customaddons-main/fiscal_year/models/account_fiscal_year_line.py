# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountFiscalYearLine(models.Model):
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _name = 'account.fiscal.year.line'
    _description = 'Periodo de Año Fiscal'

    company_id = fields.Many2one(related="period_id.company_id", store=True, readonly=False,tracking=True)
    period_id = fields.Many2one("account.fiscal.year", "Año Fiscal", ondelete="cascade")
    year = fields.Integer("Año", required=True, tracking=True)
    month_id = fields.Many2one("calendar.month", "Mes", required=True, tracking=True)
    name = fields.Char(string='Periodo', required=True, tracking=True)
    date_from = fields.Date(string='Fecha Inicial', required=True, tracking=True)
    date_to = fields.Date(string='Fecha Final', required=True, tracking=True)
    state = fields.Selection(
        [('draft', 'Preliminar'), ('open', 'Abierto'), ('in_closing', 'En cierre'), ('closed', 'Cerrado')],
        string="Estado", default="draft", tracking=True
        )
    for_account_move = fields.Boolean(string='Asientos,Facturas,etc...', default=False,tracking=True)
    for_account_payment = fields.Boolean(string='Pagos/Cobros', default=False,tracking=True)
    for_stock_move_line = fields.Boolean(string='Mov. de Inventario', default=False,tracking=True)

    _order = "date_from asc"

    def action_draft(self):
        for brw_each in self:
            brw_each.test_parent()
            brw_each.write({"state": "draft","for_account_payment":False, "for_account_move": False, "for_stock_move_line": False})
        return True

    def action_in_closing(self):
        for brw_each in self:
            brw_each.test_parent()
            brw_each.write({"state": "in_closing","for_account_payment":False, "for_account_move": False, "for_stock_move_line": False})
        return True

    def action_closed(self):
        for brw_each in self:
            brw_each.test_parent()
            brw_each.write({"state": "closed", "for_account_payment":False,"for_account_move": False, "for_stock_move_line": False})
        return True

    def action_open(self):
        for brw_each in self:
            #######################
            if brw_each.state=='in_closing':
                if not self.env.user.has_group('fiscal_year.group_reapertura'):
                    raise ValidationError(_("No puedes usar esta accion contacta con un usuario habilitado!!"))
            ######################
            brw_each.test_parent()
            brw_each.write({"state": "open", "for_account_payment":False,"for_account_move": False, "for_stock_move_line": False})
        return True

    def test_parent(self):
        for brw_each in self:
            if brw_each.period_id.state != 'open':
                raise ValidationError(_("El  Año Fiscal de %s debe estar 'Abierto' para realizar esta acción") % (
                brw_each.company_id.name,))
        return True

    def get_periods(self, date, brw_company, for_account_move=False, for_stock_move_line=False,for_account_payment=False,with_raise=True):
        self._cr.execute("""select fyl.id as period_line_id,
fyl.state ,
fyl.for_account_move,
fyl.for_stock_move_line,
fyl.for_account_payment 
from  account_fiscal_year fy
inner join account_fiscal_year_line fyl on fyl.period_id=fy.id 
where 
fy.company_id=%s and fy.state='open' 
and %s::DATE>=fyl.date_from and %s::DATE<=fyl.date_to and
    (
       fyl.state in ('open','in_closing')  
    ) """, (brw_company.id, date, date))
        result = self._cr.fetchall()
        if not result:
            raise ValidationError(
                _("No hay periodo existentes o habilitados para la fecha %s en %s") % (date, brw_company.name))
        if len(result) > 1:
            raise ValidationError(_("Existe más de un periodo para la fecha %s en %s") % (date, brw_company.name))
        result = result[0]
        brw_period_line = self.sudo().browse(result[0])
        list_index = []
        if for_stock_move_line:
            list_index += [(3, 'Movimientos de Inventario')]
        if for_account_payment:
            list_index += [(4, 'Pagos/Cobros')]
        if for_account_move:
            list_index += [(2, 'Documentos Contables')]
        for index, dcsr in list_index:
            if not (result[1] == "open" or (result[1] == "in_closing" and result[index])):
                COLUMNS = self._fields.copy()
                STATES_DSCR = dict(COLUMNS["state"].selection)
                raise ValidationError(
                    _("El periodo %s para la fecha %s no esta abierto ni habilitado para %s.Actualmente su estado es %s en %s") % (
                    brw_period_line.name, date, dcsr, STATES_DSCR[result[1]], brw_company.name))
        return brw_period_line.period_id, brw_period_line

    def write(self, vals):
        # lógica personalizada antes de la escritura
        for brw_each in self:
            if brw_each.state=='in_closing':
                if "for_account_move" in vals or "for_account_payment" in vals or "for_stock_move_line" in vals:
                    if vals.get("for_account_move",False) or vals.get("for_account_payment",False)  or vals.get("for_stock_move_line",False):
                        if not self.env.user.has_group('fiscal_year.group_reapertura'):
                            raise ValidationError(_("No puedes usar esta accion contacta con un usuario habilitado!!"))
        res = super(AccountFiscalYearLine, self).write(vals)
        # lógica personalizada después de la escritura
        return res


