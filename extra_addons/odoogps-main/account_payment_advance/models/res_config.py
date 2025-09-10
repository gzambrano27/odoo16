#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models


_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    account_default_customer_prepayment_id = fields.Many2one(
        comodel_name="account.account",
        string="Prepayment Customer account",
        domain="[('deprecated','=',False), ('prepayment_account','=',True)]",
        readonly=False,
        related="company_id.account_default_customer_prepayment_id",
        help="Counterpart for the prepayment move, for example: Prepayment for customers",
    )
    account_default_supplier_prepayment_id = fields.Many2one(
        comodel_name="account.account",
        string="Prepayment Supplier account",
        domain="[('deprecated','=',False), ('prepayment_account','=',True)]",
        readonly=False,
        related="company_id.account_default_supplier_prepayment_id",
        help="Counterpart for the prepayment move, for example: Prepayment for suppliers",
    )
