# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class L10nLatamIdentificationType(models.Model):
    _inherit = 'l10n_latam.identification.type'

    l10n_ec_code = fields.Char("Codigo")