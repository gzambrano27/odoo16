#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied


_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.constrains("state", "location_id", "location_dest_id")
    def check_user_location_rights(self):
        for row in self:
            if row.state == "draft":
                return True
            user_locations = self.env.user.stock_location_ids
            if row.move_orig_ids:
                user_locations |= row.location_id
                user_locations |= row.location_dest_id
            if row.env.user.restrict_locations:
                message = _(
                    "Invalid Location. You cannot process this move since you do "
                    'not control the location "%s". '
                    "Please contact your Adminstrator."
                )
                if row.location_id not in user_locations:
                    raise AccessDenied(message % row.location_id.name_get()[0][1])
                elif row.location_dest_id not in user_locations:
                    raise AccessDenied(message % row.location_dest_id.name_get()[0][1])

    def _action_done(self, cancel_backorder=False):
        if self.user_has_groups("stock_security.group_restrict_warehouse"):
            self = self.sudo()
        return super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
