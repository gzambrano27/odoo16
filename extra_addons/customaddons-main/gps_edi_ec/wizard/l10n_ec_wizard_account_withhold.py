# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar
from collections import defaultdict
from datetime import date

from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare

from odoo.addons.l10n_ec_edi.models.account_tax import L10N_EC_TAXSUPPORTS
from odoo.addons.l10n_ec_edi.models.account_move import L10N_EC_WTH_FOREIGN_GENERAL_REGIME_CODES
from odoo.addons.l10n_ec_edi.models.account_move import L10N_EC_WTH_FOREIGN_TAX_HAVEN_OR_LOWER_TAX_CODES
from odoo.addons.l10n_ec_edi.models.account_move import L10N_EC_WTH_FOREIGN_SUBJECT_WITHHOLD_CODES
from odoo.addons.l10n_ec_edi.models.account_move import L10N_EC_WTH_FOREIGN_DOUBLE_TAXATION_CODES
from odoo.addons.l10n_ec_edi.models.account_move import L10N_EC_WITHHOLD_FOREIGN_REGIME


class L10nEcWizardAccountWithhold(models.TransientModel):
    _inherit = 'l10n_ec.wizard.account.withhold'

    def _validate_helper_for_foreign_tax_codes(self):

        return False