#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied


_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model_create_multi
    def create(self, vals_list):
        if self.user_has_groups("stock_security.group_product_restrict"):
            raise AccessDenied(
                _(
                    "You do not have access to create products, please contact the administrator!"
                )
            )
        return super().create(vals_list)


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model_create_multi
    def create(self, vals_list):
        if self.user_has_groups("stock_security.group_product_restrict"):
            raise AccessDenied(
                _(
                    "You do not have access to create products, please contact the administrator!"
                )
            )
        return super().create(vals_list)
