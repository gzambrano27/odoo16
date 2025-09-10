# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from odoo.exceptions import ValidationError,UserError

from odoo import api, fields, models, _

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'


    analytic_account_names = fields.Char(
        string='Cuentas Analíticas',
        compute='_compute_analytic_account_names',
        store=True
    )


    @api.depends('analytic_distribution')
    def _compute_analytic_account_names(self):
        for line in self:
            if isinstance(line.analytic_distribution, dict):
                # Obtiene los IDs de las cuentas analíticas
                analytic_account_ids = list(line.analytic_distribution.keys())
                # Busca los nombres de las cuentas analíticas utilizando esos IDs
                analytic_accounts = self.env['account.analytic.account'].search([('id', 'in', analytic_account_ids)])
                line.analytic_account_names = ', '.join(analytic_accounts.mapped('name'))
            else:
                line.analytic_account_names=''

    def _action_done(self):
        values=super(StockMoveLine,self)._action_done()
        return values
