# Copyright 2014 Akretion - Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2014 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ec_payment_id = fields.Many2one('l10n_ec.sri.payment', 'Metodo de Pago SRI')
    verificado = fields.Boolean('Verificado?')
    