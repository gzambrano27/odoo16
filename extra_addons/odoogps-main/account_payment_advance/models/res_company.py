#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models


_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    account_default_customer_prepayment_id = fields.Many2one(
        comodel_name="account.account",
        string="Prepayment account",
        domain="[('deprecated','=',False), ('prepayment_account','=',True)]",
    )
    account_default_supplier_prepayment_id = fields.Many2one(
        comodel_name="account.account",
        string="Prepayment account",
        domain="[('deprecated','=',False), ('prepayment_account','=',True)]",
    )
