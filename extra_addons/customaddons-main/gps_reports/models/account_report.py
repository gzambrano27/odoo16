# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import datetime
import io
import json
import logging
import math
import re
import base64
from ast import literal_eval
from collections import defaultdict
from functools import cmp_to_key

import markupsafe
from babel.dates import get_quarter_names
from dateutil.relativedelta import relativedelta

from odoo.addons.web.controllers.utils import clean_action
from odoo import models, fields, api, _, osv
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import config, date_utils, get_lang, float_compare, float_is_zero
from odoo.tools.float_utils import float_round
from odoo.tools.misc import formatLang, format_date, xlsxwriter
from odoo.tools.safe_eval import expr_eval, safe_eval
from odoo.models import check_method_name

_logger = logging.getLogger(__name__)

class AccountReport(models.Model):

    _inherit = 'account.report'

    mail_model_name=fields.Char(required=False,default="account.move.line")
    main_model_name = fields.Char('Modelo', required=False, default="account.move.line")

    @api.model
    def _check_groupby_fields(self, groupby_fields_name):
        # print(self)
        # """ Checks that each string in the groupby_fields_name list is a valid groupby value for an accounting report (so: it must be a field from
        # account.move.line).
        # """
        main_model_name=self.main_model_name or None
        if main_model_name is None or not main_model_name or len(main_model_name)<=0:
            return
        for field_name in groupby_fields_name:
            groupby_field = self.env[main_model_name]._fields.get(field_name)
            if not groupby_field:
                raise UserError(_("Field %s does not exist on %s.", field_name,main_model_name))
            if not groupby_field.store:
                raise UserError(
                    _("Field %s of %s is not stored, and hence cannot be used in a groupby expression",
                      field_name,main_model_name))

    def _parse_groupby(self, groupby_to_expand=None):
        """ Retrieves the information needed to handle the groupby feature on the current line.

        :param groupby_to_expand:    A coma-separated string containing, in order, all the fields that are used in the groupby we're expanding.
                                     None if we're not expanding anything.

        :return: A dictionary with 3 keys:
            'current_groupby':       The name of the field to be used on account.move.line to retrieve the results of the current groupby we're
                                     expanding, or None if nothing is being expanded

            'next_groupby':          The subsequent groupings to be applied after current_groupby, as a string of coma-separated field name.
                                     If no subsequent grouping exists, next_groupby will be None.

            'current_groupby_model': The model name corresponding to current_groupby, or None if current_groupby is None.

        EXAMPLE:
            When computing a line with groupby=partner_id,account_id,id , without expanding it:
            - groupby_to_expand will be None
            - current_groupby will be None
            - next_groupby will be 'partner_id,account_id,id'
            - current_groupby_model will be None

            When expanding the first group level of the line:
            - groupby_to_expand will be: partner_id,account_id,id
            - current_groupby will be 'partner_id'
            - next_groupby will be 'account_id,id'
            - current_groupby_model will be 'res.partner'

            When expanding further:
            - groupby_to_expand will be: account_id,id ; corresponding to the next_groupby computed when expanding partner_id
            - current_groupby will be 'account_id'
            - next_groupby will be 'id'
            - current_groupby_model will be 'account.account'
        """
        self.ensure_one()
        main_model_name = self.main_model_name or None
        if main_model_name is None or not main_model_name or len(main_model_name) <= 0:
            main_model_name="account.move.line"
        if groupby_to_expand:
            groupby_to_expand = groupby_to_expand.replace(' ', '')
            split_groupby = groupby_to_expand.split(',')
            current_groupby = split_groupby[0]
            next_groupby = ','.join(split_groupby[1:]) if len(split_groupby) > 1 else None
        else:
            current_groupby = None
            next_groupby = self.groupby.replace(' ', '') if self.groupby else None
            split_groupby = next_groupby.split(',') if next_groupby else []

        if current_groupby == 'id':
            groupby_model = main_model_name
        elif current_groupby:
            groupby_model = self.env[main_model_name]._fields[current_groupby].comodel_name
        else:
            groupby_model = None

        return {
            'current_groupby': current_groupby,
            'next_groupby': next_groupby,
            'current_groupby_model': groupby_model,
        }

    def action_open_main(self, options, params):
        import re
        match = re.search(r'~([\w\.]+)~(\d+)}?$', params.get('id',''))
        if match:
            model_name = match.group(1)  # 'document.financial'
            return self.env[model_name].action_open_main( options, params)
        raise ValidationError(_("No fue posible identificar el ID"))