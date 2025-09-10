# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from json import dumps

from odoo import _, api, fields, models
from datetime import datetime, timedelta

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_ec_withhold_tax_amount = fields.Monetary(
        string="Withhold Tax Amount",
        compute='_compute_withhold_tax_amount', store=True
    )

    l10n_ec_withhold_tax_percn = fields.Float(
        string="% Retencion",compute='_compute_withhold_tax_amount', store=True, digits=(16, 4)
    )

    @api.model
    def redondear_abajo(self,numero):
        import math
        numero_redondeado = math.floor(numero * 100) / 100
        return numero_redondeado

    @api.depends('tax_ids')
    def _compute_withhold_tax_amount(self):
        for line in self.filtered('move_id.l10n_ec_withhold_type'):
            currency_rate = line.balance / line.amount_currency if line.amount_currency != 0 else 1
            line.l10n_ec_withhold_tax_amount = line.currency_id.round(
                currency_rate * abs(line.price_total - line.price_subtotal))
            l10n_ec_withhold_tax_percn=0.00
            if not line.tax_ids:
                l10n_ec_withhold_tax_percn=(line.balance!=0.00) and (
                        self.redondear_abajo( (line.l10n_ec_withhold_tax_amount /line.balance)*100.00)
                ) or 0.00
            else:
                if len(line.tax_ids)>1:
                    l10n_ec_withhold_tax_percn = (line.balance != 0.00) and (
                        self.redondear_abajo((line.l10n_ec_withhold_tax_amount / line.balance) * 100.00)
                    ) or 0.00
                else:#si es solo 1 se asigna el porcentaje
                    for brw_line_tax in line.tax_ids:
                        l10n_ec_withhold_tax_percn=abs(brw_line_tax.amount)
                        continue
            line.l10n_ec_withhold_tax_percn=l10n_ec_withhold_tax_percn



    _order = "id asc"
