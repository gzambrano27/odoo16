#!/usr/bin/env python
# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import Warning


class ResUsers(models.Model):
    _inherit = "res.users"

    restrict_locations = fields.Boolean(string=_("Restrict Location"))
    all_warehouse = fields.Boolean(string=_("All Warehouse Access"))

    stock_location_ids = fields.Many2many(
        comodel_name="stock.location",
        relation="location_security_stock_location_users",
        column1="user_id",
        column2="location_id",
        string=_("Stock Locations"),
    )
    default_warehouse_ids = fields.Many2many(
        comodel_name="stock.warehouse",
        relation="stock_warehouse_users_rel",
        column1="user_id",
        column2="warehouse_id",
        string="Default Warehouse",
    )
    default_picking_type_ids = fields.Many2many(
        comodel_name="stock.picking.type",
        relation="stock_picking_type_users_rel",
        column1="user_id",
        column2="picking_type_id",
        string="Default Warehouse Operations",
    )
