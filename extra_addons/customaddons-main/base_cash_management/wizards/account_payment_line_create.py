#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models


_logger = logging.getLogger(__name__)


class AccountPaymentLineCreate(models.TransientModel):
    _inherit = "account.payment.line.create"

    @api.model
    def default_get(self, field_list):
        res = super(AccountPaymentLineCreate, self).default_get(field_list)
        res.update({"due_date": fields.Date.today(), "payment_mode": "any"})
        return res
