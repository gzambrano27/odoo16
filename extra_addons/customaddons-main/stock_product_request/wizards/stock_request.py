#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from base64 import b64decode
from io import BytesIO

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError
from openpyxl_dictreader import DictReader


_logger = logging.getLogger(__name__)


class StockRequestWizard(models.TransientModel):
    """Wizard to generate inventory requests from a file."""

    _name = "stock.request.wizard"
    _description = __doc__

    def _get_options(self):
        return [("import", _("Import Template")), ("export", _("Export Template"))]

    company_id = fields.Many2one(
        "res.company",
        "Company",
        required=True,
        readonly=True,
        default=lambda self: self.env["res.company"]._company_default_get(
            "stock.request.order.line"
        ),
    )
    requested_by = fields.Many2one(
        "res.users",
        "Requested by",
        required=True,
        default=lambda self: self.env.user,
    )
    picking_policy = fields.Selection(
        [
            ("direct", "Receive each product when available"),
            ("one", "Receive all products at once"),
        ],
        string="Shipping Policy",
        required=True,
        default="direct",
        track_visibility="onchange",
    )
    expected_date = fields.Datetime(
        "Expected Date",
        default=fields.Datetime.now,
        required=True,
        help="Date when you expect to receive the goods.",
    )
    allow_negative = fields.Boolean(
        "Allow Negative",
    )
    priority = fields.Selection(
        [("0", "Not urgent"), ("1", "Normal"), ("2", "Urgent"), ("3", "Very urgent")],
        default="1",
        required=True,
    )
    name = fields.Char(_("Name"))
    xlsx_file = fields.Binary(_("Xlsx File"))
    option = fields.Selection(selection=_get_options, string=_("Option"))
    wh_from = fields.Many2one("stock.warehouse", string=_("From"))
    wh_to = fields.Many2many("stock.warehouse", string=_("To"))

    def button_export(self):
        context = self._context
        datas = {"ids": context.get("active_ids", [])}
        datas["model"] = self._name
        datas["form"] = self.read()[0]
        for field in datas["form"].keys():
            if isinstance(datas["form"][field], tuple):
                datas["form"][field] = datas["form"][field][0]
        return self.env.ref(
            "stock_request_product.stock_request_template_xlsx"
        ).report_action(self, data=datas)

    def button_import(self):
        request_obj = self.env["stock.request.product"]
        wh_obj = self.env["stock.warehouse"]
        product_obj = self.env["product.product"]
        vals = {}
        for row in self:
            if not row.xlsx_file:
                raise UserError(_("Please, select file to Import"))
            data = b64decode(row.xlsx_file)
            file_input = BytesIO(data)
            file_input.seek(0)
            try:
                reader = DictReader(file_input, read_only=True, data_only=True)
            except Exception:
                raise ValidationError(
                    _("The file to import must have an xlsx extension!")
                )
            for req in reader:
                domain = []
                if req.get("CODE", False) or req.get("BARCODE"):
                    if req.get("CODE", False):
                        domain.append(("default_code", "=", req.get("CODE", False)))
                    if req.get("BARCODE"):
                        domain.append(("barcode", "=", req.get("BARCODE", False)))
                    product_id = product_obj.search(domain)
                    if not product_id:
                        continue
                    wh_id = wh_obj.search([("code", "=", req.get("WAREHOUSE", False))])
                    if not wh_id:
                        continue
                    if wh_id not in vals:
                        vals.update({wh_id: {}})
                    move_type = req.get("TYPE", False)
                    if move_type not in vals[wh_id]:
                        vals[wh_id].update({move_type: []})
                    for key in req:
                        if key is None:
                            continue
                        if not req[key]:
                            req[key] = 0
                        if "|" in key and isinstance(req[key], str):
                            if req[key].isnumeric():
                                req[key] = str(req[key])
                            else:
                                req[key] = 0
                        if "|" in key and req[key] > 0:
                            wh_code = key.split("|")[0]
                            wh_dest_id = wh_obj.search([("code", "=", wh_code)])
                            move_vals = self.get_route_data(
                                product_id, req[key], wh_id, wh_dest_id, move_type
                            )
                            if move_vals.get("location_id", False):
                                vals[wh_id][move_type].append((0, 0, move_vals))
        if vals:
            request = request_obj
            for wh, moves in vals.items():
                for mtype, lines in moves.items():
                    req_vals = {
                        "warehouse_id": wh.id,
                        "expected_date": self.expected_date,
                        "picking_policy": self.picking_policy,
                        "type": mtype,
                        "priority": self.priority,
                        "allow_negative": self.allow_negative,
                        "line_ids": lines,
                    }
                    request |= request_obj.create(req_vals)
            if request:
                action = self.env.ref(
                    "stock_request_product.action_stock_request_product"
                ).read()[0]
                action["domain"] = [("id", "in", request.ids)]
                return action
        return True

    def get_route_data(self, product, qty, wh_org_id, wh_dest_id, move_type):
        req_obj = self.env["stock.request.product.line"]
        res = {
            "product_id": product.id,
            "product_uom_qty": qty,
            "product_uom": product.uom_id.id,
            "route_id": "",
            "warehouse_id": wh_org_id.id,
            "type": move_type,
            "location_id": "",
            "location_src_id": "",
            "location_dest_id": "",
            "location_trans_id": "",
            "in_picking_type_id": "",
            "out_picking_type_id": "",
        }
        location = wh_org_id.lot_stock_id
        if move_type == "send":
            location = wh_dest_id.lot_stock_id
        route_ids = req_obj._get_routes(wh_org_id, product, location, type=move_type)
        if move_type == "send":
            route_id = route_ids.filtered(
                lambda x: wh_dest_id in x.rule_ids.mapped("warehouse_id")
            )
        else:
            route_id = route_ids.filtered(
                lambda x: wh_org_id in x.rule_ids.mapped("warehouse_id")
            )
        if route_id:
            dest, src, trans, out_type, in_type = req_obj._prepare_locations(
                move_type, route_id, loc_dest=location
            )
            res.update(
                {
                    "route_id": route_id.id,
                    "type": move_type,
                    "location_id": location.id,
                    "location_src_id": src.id,
                    "location_dest_id": dest.id,
                    "location_trans_id": trans.id,
                    "in_picking_type_id": in_type.id,
                    "out_picking_type_id": out_type.id,
                }
            )
        return res
