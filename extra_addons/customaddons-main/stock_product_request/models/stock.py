# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import datetime

import pytz
from odoo import _, api, fields, models
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


REQUEST_STATES = [
    ("draft", "Draft"),
    ("open", "In progress"),
    ("done", "Done"),
    ("cancel", "Cancelled"),
]


def clean_str(dirty_string):
    return "".join(list(s for s in dirty_string if s.isprintable()))


class StockProductRequest(models.Model):
    """Stock Product Request"""

    _name = "stock.product.request"
    _description = __doc__
    _inherit = ["multi.company.abstract", "mail.thread", "mail.activity.mixin"]
    _check_company_auto = True
    _order = "id desc"

    name = fields.Char(
        string=_("Name"),
        copy=False,
        required=True,
        readonly=True,
        tracking=True,
        states={"draft": [("readonly", False)]},
        default="/",
    )
    state = fields.Selection(
        selection=REQUEST_STATES,
        string=_("Status"),
        copy=False,
        default="draft",
        readonly=True,
        tracking=True,
    )
    requested_by = fields.Many2one(
        comodel_name="res.users",
        string=_("Requested by"),
        required=True,
        tracking=True,
        default=lambda self: self.env.user,
    )
    move_type = fields.Selection(
        selection=[
            ("direct", "Receive each product when available"),
            ("one", "Receive all products at once"),
        ],
        string=_("Shipping Policy"),
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        default="direct",
        tracking=True,
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string=_("Warehouse"),
        readonly=True,
        ondelete="cascade",
        required=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )
    date_from = fields.Date(
        string="From",
        default=fields.Date.today,
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )
    date_to = fields.Date(
        string="To",
        default=fields.Date.today,
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )
    expected_date = fields.Datetime(
        "Expected Date",
        default=fields.Datetime.now,
        index=True,
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="Date when you expect to receive the goods.",
        tracking=True,
    )
    type = fields.Selection(
        [("bring", "Bring"), ("send", "Send")],
        default="send",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )
    priority = fields.Selection(
        selection=PROCUREMENT_PRIORITIES,
        default="0",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )
    allow_negative = fields.Boolean(
        string=_("Allow Negative"),
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    move_ids = fields.One2many(
        comodel_name="stock.move", inverse_name="request_id", string="Moves"
    )
    move_count = fields.Integer(string="Operations", compute="_compute_operations")
    picking_ids = fields.One2many(
        comodel_name="stock.picking",
        inverse_name="request_id",
        string="Pickings",
        readonly=True,
    )
    picking_count = fields.Integer(
        string="Delivery Orders", compute="_compute_operations"
    )
    backorder_ids = fields.One2many(
        comodel_name="stock.picking",
        inverse_name="request_id",
        domain=[("backorder_id", "!=", False)],
    )
    backorder_count = fields.Integer(string="Backorders", compute="_compute_operations")
    line_count = fields.Integer(string="Request count", compute="_compute_operations")
    line_ids = fields.One2many(
        comodel_name="stock.product.request.line",
        inverse_name="request_id",
        string=_("Product Request"),
        copy=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    origin = fields.Char(
        string="Origin",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        related="line_ids.product_id",
        string="Product",
        readonly=False,
    )
    route_id = fields.Many2one(
        "stock.route",
        related="line_ids.route_id",
        string="Route",
        readonly=False,
    )
    company_id = fields.Many2one(default=lambda self: self.env.company)

    def action_print_stock_request(self):
        return self.env.ref("stock_product_request.stock_request_report").report_action(
            self
        )

    def action_print_delivery(self):
        pickings = self.env["stock.picking"]
        for row in self:
            if row.type == "send":
                pickings |= row.mapped("picking_ids").filtered(
                    lambda x: x.picking_type_id.warehouse_id == row.warehouse_id
                )
            else:
                pickings |= row.mapped("picking_ids").filtered(
                    lambda x: x.picking_type_id.warehouse_id != row.warehouse_id
                )
        return self.env.ref("stock.action_report_delivery").report_action(pickings)

    @api.depends(
        "line_ids", "picking_ids", "picking_ids.state", "move_ids", "move_ids.state"
    )
    def _compute_operations(self):
        for row in self:
            row.line_count = row.line_ids and len(row.line_ids) or 0
            row.picking_count = row.picking_ids and len(row.picking_ids) or 0
            row.backorder_count = row.backorder_ids and len(row.backorder_ids) or 0
            row.move_count = len(row.move_ids) or 0
            if row.picking_ids:
                row.check_done()
        return True

    def action_view_request_product_line(self):
        module = __name__.split("addons.")[1].split(".")[0]
        action_name = "{}.action_stock_request_product_line".format(module)
        action = self.sudo().env.ref(action_name, False).sudo().read()[0]
        lines = self.mapped("line_ids")
        if len(lines) > 1:
            action["domain"] = [("id", "in", lines.ids)]
        else:
            action["views"] = [
                (
                    self.sudo()
                    .env.ref("{}.view_stock_product_request_line_form".format(module))
                    .id,
                    "form",
                ),
            ]
            action["res_id"] = lines.id
        return action

    def action_view_transfer(self):
        action = self.env.ref("stock.action_picking_tree_all").sudo().read()[0]
        pickings = self.mapped("picking_ids")
        if len(pickings) > 1:
            route_less = pickings.filtered(lambda x: not x.route_request)
            action["domain"] = [("id", "in", pickings.ids)]
            if not route_less:
                action["context"] = {"group_by": "route_request"}
        elif pickings:
            action["views"] = [
                (self.env.ref("stock.view_picking_form").id, "form"),
            ]
            action["res_id"] = pickings.id
        else:
            return True
        return action

    def action_view_backorder(self):
        action = self.sudo().env.ref("stock.action_picking_tree_all").sudo().read()[0]
        pickings = self.mapped("backorder_ids")
        if len(pickings) > 1:
            action["domain"] = [("id", "in", pickings.ids)]
        elif pickings:
            action["views"] = [
                (self.sudo().env.ref("stock.view_picking_form").id, "form"),
            ]
            action["res_id"] = pickings.id
        else:
            return True
        return action

    def action_view_moves(self):
        action = self.sudo().env.ref("stock.stock_move_action").sudo().read()[0]
        moves = self.mapped("move_ids")
        if len(moves) > 1:
            action["domain"] = [("id", "in", moves.ids)]
        elif moves:
            action["views"] = [(self.env.ref("stock.view_move_form").id, "form")]
            action["res_id"] = moves.id
        else:
            return True
        return action

    def action_check_assign_all(self):
        action = (
            self.sudo()
            .env.ref("stock_picking_mass_action.action_transfer")
            .sudo()
            .read()[0]
        )
        pickings = self.mapped("picking_ids").filtered(
            lambda x: x.picking_type_id.warehouse_id == self.warehouse_id
        )
        action["context"] = {"active_ids": pickings.ids}
        return action

    @api.onchange("warehouse_id")
    def _onchange_warehouse_id(self):
        for row in self:
            if not self.env.context.get("no_wh_change", False):
                if row.line_ids:
                    for line in row.line_ids:
                        line.update(
                            {
                                "warehouse_id": row.warehouse_id.id,
                                "route_id": None,
                                "location_dest_id": None,
                                "location_src_id": None,
                                "location_trans_id": None,
                                "out_picking_type_id": None,
                                "in_picking_type_id": None,
                            }
                        )
                        line._onchange_location_id()

    @api.onchange("type")
    def _onchange_type(self):
        for row in self:
            if row.line_ids:
                for line in row.line_ids:
                    line.update({"type": row.type})
                    line._onchange_route_id()

    def action_confirm(self):
        picking_obj = self.env["stock.picking"]
        tz = self.env.user.tz or pytz.UTC.zone
        for row in self:
            origin = row.name
            if (
                any(row.line_ids.filtered(lambda x: x.product_uom_qty_residual < 0))
                and not row.allow_negative
            ):
                raise UserError(
                    _(
                        "¡You can not create picking for Warehouse {}, while you have a negative balance!".format(
                            row.warehouse_id.name
                        )
                    )
                )
            if origin == "/":
                origin = self.env["ir.sequence"].next_by_code("stock.product.request")
            if not row.line_ids:
                raise UserError(_("You need at least one move line to process"))

            def base_dict():
                return defaultdict(base_dict)

            pdata = base_dict()
            for line in row.line_ids:
                route = line.route_id.id
                date = datetime.combine(line.expected_date, datetime.max.time())
                date = (
                    pytz.timezone(tz)
                    .localize(date, is_dst=None)
                    .strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                )
                prod = line.product_id.id
                if not pdata[date][route]:
                    pdata[date][route].update(
                        {
                            "location_dest_id": None,
                            "location_src_id": None,
                            "location_trans_id": None,
                            "out_picking_type_id": None,
                            "in_picking_type_id": None,
                            "products": {},
                        }
                    )

                pdata[date][route]["location_dest_id"] = line.location_dest_id
                pdata[date][route]["location_src_id"] = line.location_src_id
                pdata[date][route]["location_trans_id"] = line.location_trans_id
                pdata[date][route]["out_picking_type_id"] = line.out_picking_type_id
                pdata[date][route]["in_picking_type_id"] = line.in_picking_type_id
                pdata[date][route]["products"][prod] = pdata[date][route][
                    "products"
                ].get(prod, {"product": None, "uom": None, "qty": 0})
                pdata[date][route]["products"][prod]["product"] = line.product_id
                pdata[date][route]["products"][prod]["uom"] = line.product_uom
                pdata[date][route]["products"][prod]["qty"] += line.product_uom_qty
            for expected, pick_data in pdata.items():
                for pick in pick_data.values():
                    src = pick.get("location_src_id", False)
                    dest = pick.get("location_dest_id", False)
                    trans = pick.get("location_trans_id", False)
                    moves = pick.get("products", False)
                    in_type = pick.get("in_picking_type_id", False)
                    out_type = pick.get("out_picking_type_id", False)
                    move_obj = self.env["stock.move"]
                    out_picking = self.env["stock.picking"]
                    route_request = "{} -> {}".format(
                        out_type.sudo().warehouse_id.name,
                        in_type.sudo().warehouse_id.name,
                    )
                    if trans:
                        name = out_type.sudo().sequence_id.next_by_id()
                        out_picking = picking_obj.sudo().create(
                            {
                                "name": name,
                                "origin": origin,
                                "request_id": row.id,
                                "route_request": route_request,
                                "picking_type_id": out_type.id,
                                "move_type": row.move_type,
                                "priority": row.priority,
                                "location_dest_id": trans.id,
                                "location_id": src.id,
                                "scheduled_date": expected,
                                "company_id": row.company_id.id,
                            }
                        )
                    name = in_type.sudo().sequence_id.next_by_id()
                    in_picking = self.env["stock.picking"]
                    in_picking = picking_obj.sudo().create(
                        {
                            "name": name,
                            "origin": origin,
                            "request_id": row.id,
                            "route_request": route_request,
                            "picking_type_id": in_type.id,
                            "move_type": row.move_type,
                            "priority": row.priority,
                            "location_dest_id": dest.id,
                            "location_id": trans.id if trans else src.id,
                            "scheduled_date": expected,
                            "company_id": row.company_id.id,
                        }
                    )
                    for move in moves.values():
                        product = move.get("product", False)
                        uom = move.get("uom", False)
                        qty = move.get("qty", 0)
                        if qty > 0:
                            in_move = move_obj.sudo().create(
                                {
                                    "location_id": in_picking.location_id.id,
                                    "location_dest_id": in_picking.location_dest_id.id,
                                    "product_id": product.id,
                                    "product_uom": uom.id,
                                    "product_uom_qty": qty,
                                    "name": _("Supply move for: ") + origin,
                                    "request_id": row.id,
                                    "state": "draft",
                                    "picking_id": in_picking.id,
                                    "date_deadline": expected,
                                    "company_id": row.company_id.id,
                                }
                            )
                            if out_picking:
                                move_obj.sudo().create(
                                    {
                                        "location_id": out_picking.location_id.id,
                                        "location_dest_id": out_picking.location_dest_id.id,
                                        "product_id": product.id,
                                        "product_uom": uom.id,
                                        "product_uom_qty": qty,
                                        "name": _("Supply move for: ") + origin,
                                        "request_id": row.id,
                                        "state": "draft",
                                        "picking_id": out_picking.id,
                                        "move_dest_ids": [(6, 0, in_move.ids)],
                                        "date_deadline": expected,
                                        "company_id": row.company_id.id,
                                    }
                                )
                    in_picking.sudo().action_confirm()
                    if out_picking:
                        out_picking.sudo().action_confirm()
                row.name = origin
                row.state = "open"
        return True

    def action_draft(self):
        self.state = "draft"
        return True

    def action_cancel(self):
        for line in self.picking_ids.filtered(
            lambda x: x.state not in ["done", "cancel"]
        ):
            line.action_cancel()
        self.state = "cancel"
        return True

    def check_done(self):
        if not self.picking_ids.filtered(lambda r: r.state not in ["done", "cancel"]):
            self.write({"state": "done"})
        return True

    def unlink(self):
        if self.filtered(lambda r: r.state != "draft"):
            raise UserError(_("Only orders on draft state can be unlinked"))
        return super().unlink()

    @api.model
    def get_request_data(self, request):
        wh_ids = (
            self.mapped("line_ids.route_id.rule_ids")
            .filtered(lambda x: x.procure_method == "make_to_order")
            .mapped("warehouse_id")
            .sorted(lambda x: x.code)
        )
        res = """
        <table style="width: 100%;">
          <thead>
            <tr>
              <th style="text-align: center;">
                STOCK REQUEST: {srp} | {date}
               </th>
             </tr>
          </thead>
        </table>
        <table class="table table-sm" style="width: 100%; border-collapse: collapse; border: 1px solid black; page-break-after:always;">
          <thead style="font-size: 10px;">
            <tr style="border: 1px solid black;">
              <th style="border: 1px solid black; padding-right: 0.5em;">SKU</th>
              <th style="border: 1px solid black; padding-right: 0.5em;">CANT.</th>
        """.format(
            srp=self.name, date=self.expected_date, cols=(2 + 4 * len(wh_ids))
        )
        if wh_ids:
            for wh in wh_ids:
                res += """
                <th style="border: 1px solid black; padding-right: 0.5em; color: red;">{}</th>
                <th style="border: 1px solid black; padding-right: 0.5em;">DESP</th>
                <th style="border: 1px solid black; padding-right: 0.5em;">VERIF</th>
                <th style="border: 1px solid black; padding-right: 0.5em;">O.S.</th>
                """.format(
                    wh.code
                )
        res += """
        </tr>
        </thead>
        <tbody>
        """
        query = """
		SELECT  COALESCE(pp.default_code,'') AS default_code,
				AVG(srpl.product_uom_qty_current) AS qty_available,
				ARRAY_TO_JSON(ARRAY(SELECT concat(pp.default_code,'-',sw.code, ':', srpl2.product_uom_qty)
									  FROM stock_product_request_line srpl2
										   join product_product pp ON
												  srpl2.product_id = pp.id
										   join stock_route slr ON
												  srpl2.route_id = slr.id
										   join stock_rule sr ON
												  sr.route_id = slr.id
											   AND sr.procure_method = 'make_to_order'
										   JOIN stock_warehouse sw ON
												  sr.warehouse_id = sw.id
									 WHERE srpl2.product_id = pp.id AND
										   srpl2.request_id = {req})) AS request
		  FROM stock_product_request_line srpl
			   JOIN product_product pp ON
					  srpl.product_id = pp.id
			   JOIN product_template pt ON
					  pp.product_tmpl_id = pt.id
		 WHERE srpl.request_id = {req}
		 GROUP BY pp.id,
				  pp.default_code,
				  pt.name
        """.format(
            req=request.id
        )
        self.env.cr.execute(query)
        request_data = self.env.cr.dictfetchall()
        for req in request_data:
            res += """
            <tr>
            <td style="border: 1px solid black; padding-right: 0.5em;">
            {sku}
            </td>
            <td style="border: 1px solid black; text-align: right; padding-right: 0.5em;">
            {qty}
            </td>
            """.format(
                sku=clean_str(req.get("default_code").strip()),
                qty="{:.2f}".format(req.get("qty_available") or 0),
            )
            req_wh = req.get("request")
            for rwh in wh_ids:
                req_p = "{}-{}".format(req.get("default_code"), rwh.code)
                total_req = 0
                req_data = list(filter(lambda k: req_p in k, req_wh))
                for r in req_data:
                    total_req += float(r.split(":")[-1])
                res += """
                <td style="border: 1px solid black; text-align: right; padding-right: 0.5em;" >
                {req:.2f}
                </td>
                <td style="border: 1px solid black;" />
                <td style="border: 1px solid black;" />
                <td style="border: 1px solid black;" />
                """.format(
                    req=total_req
                )
            res += "</tr>"
        res += """
        </tbody>
        </table>
        """
        return res


class StockRequestProductLine(models.Model):
    """Stock Request Product Line"""

    _name = "stock.product.request.line"
    _inherit = ["multi.company.abstract"]
    _description = __doc__
    _order = "expected_date, route_id, product_id"

    request_id = fields.Many2one(
        comodel_name="stock.product.request",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    product_uom_qty = fields.Float(
        string="Planned Quantity",
        digits="Product Unit of Measure",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    product_uom = fields.Many2one(
        comodel_name="uom.uom",
        string=_("UoM"),
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    product_uom_qty_current = fields.Float(
        compute="_fnct_line_stock",
        string="Current Stock",
        digits="Product Unit of Measure",
        store=True,
    )
    product_uom_qty_residual = fields.Float(
        compute="_fnct_line_stock",
        string="Residual Stock",
        digits="Product Unit of Measure",
        required=True,
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string=_("Warehouse"),
        ondelete="cascade",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    type = fields.Selection(
        [("bring", "Bring"), ("send", "Send")],
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    route_ids = fields.Many2many(
        comodel_name="stock.route",
        string="Routes",
        compute="_compute_route_ids",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    route_id = fields.Many2one(
        comodel_name="stock.route",
        string=_("Route"),
        required=True,
        domain="[('id', 'in', route_ids)]",
        ondelete="restrict",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    location_id = fields.Many2one("stock.location", string="Location Aux")
    location_src_id = fields.Many2one(
        "stock.location", "Source Location", domain=[("usage", "=", "internal")]
    )
    location_dest_id = fields.Many2one(
        "stock.location", "Destination location", domain=[("usage", "=", "internal")]
    )
    location_trans_id = fields.Many2one(
        "stock.location", "Transit Location", domain=[("usage", "=", "transit")]
    )
    in_picking_type_id = fields.Many2one("stock.picking.type", "In picking type")
    out_picking_type_id = fields.Many2one("stock.picking.type", "Out picking type")
    expected_date = fields.Date(
        string="Expected Date",
        default=fields.Date.today,
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    state = fields.Selection(related="request_id.state", store=True, default="draft")

    def name_get(self):
        res = []
        for row in self:
            res.append(
                (
                    row.id,
                    "{} - {} ({} {})".format(
                        row.request_id.name,
                        row.product_id.display_name,
                        row.product_uom_qty,
                        row.product_uom.name,
                    ),
                )
            )
        return res

    def _get_product_stock(self, qty, product, location):
        quant_obj = self.env["stock.quant"]
        quant_data = []
        if location:
            quant_data = quant_obj.search(
                [
                    ("product_id", "=", product.id),
                    ("location_id", "child_of", location.id),
                ]
            )
        quant = sum(quant_data.mapped("quantity")) if len(quant_data) > 0 else 0.00
        reserved = (
            sum(quant_data.mapped("reserved_quantity")) if len(quant_data) > 0 else 0.00
        )
        quant -= reserved
        current = quant
        residual = quant - qty
        return current, residual

    @api.depends("product_uom_qty", "product_id", "route_id")
    def _fnct_line_stock(self):
        for row in self:
            product = row.product_id
            current = residual = 0
            if product:
                current, residual = self._get_product_stock(
                    row.product_uom_qty, product, self.location_src_id
                )
            row.product_uom_qty_current = current
            row.product_uom_qty_residual = residual
        return True

    @api.model
    def _prepare_locations(self, type, route, loc_dest=None):
        if route:
            # Reset all variables.
            src = self.env["stock.location"]
            trans = self.env["stock.location"]
            dest = self.env["stock.location"]
            in_type = self.env["stock.picking.type"]
            out_type = self.env["stock.picking.type"]

            procurements = route.rule_ids.filtered(
                lambda x: x.action in ["pull", "pull_push", "push"]
            )  # "move")

            loc_dest = loc_dest or self.warehouse_id.lot_stock_id

            procurement = procurements.filtered(
                lambda x: x.procure_method == "make_to_stock"
            )
            if not procurement:
                raise UserError(
                    _(
                        "At least one rule must match the destination location: {}".format(
                            loc_dest.name
                        )
                    )
                )
            procurement = procurement[0]

            trans = procurement.location_dest_id
            src = procurement.location_src_id
            out_type = procurement.picking_type_id

            propagate = procurements.filtered(
                lambda x: x.procure_method == "make_to_order"
            )
            if propagate:
                # Ensure only one rule to propagate.
                propagate = propagate[0]
                dest = propagate.location_dest_id
                in_type = propagate.picking_type_id
            if (
                type == "send"
                and src.warehouse_id.id in self.warehouse_id.resupply_wh_ids.ids
            ):
                src, dest = dest, src

                # The pickings are interchanged if type is return.
                in_return = out_type
                out_return = in_type

                # If the pickings have return types defined, use them instead.
                if out_type.sudo().return_picking_type_id:
                    in_return = out_type.sudo().return_picking_type_id
                if in_type.sudo().return_picking_type_id:
                    out_return = in_type.sudo().return_picking_type_id

                in_type = in_return
                out_type = out_return

            return dest, src, trans, out_type, in_type

    # TODO: Filter by warehouse
    @api.onchange("type", "route_id")
    def _onchange_route_id(self):
        for row in self:
            if row.route_id:
                loc_dest = row.location_dest_id
                dest, src, trans, out_type, in_type = self._prepare_locations(
                    row.type, row.route_id, loc_dest=loc_dest
                )

                vals = {
                    "location_dest_id": dest.id,
                    "location_src_id": src.id,
                    "location_trans_id": trans.id,
                    "out_picking_type_id": out_type.id,
                    "in_picking_type_id": in_type.id,
                }
                row.update(vals)

    @api.onchange("type")
    def _onchange_location_id(self):
        if self.type == "send":
            # Stock Location set to Partner Locations/Customers
            self.location_id = self.company_id.partner_id.property_stock_customer.id
        else:
            self.location_id = self.warehouse_id.lot_stock_id.id

    @api.onchange("product_id")
    def onchange_product_id(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id

    @api.model
    def get_parents(self, location):
        result = location
        while location.location_id:
            location = location.location_id
            result |= location
        return result

    @api.model
    def _get_routes(self, wh, product, location=False, type="send"):
        route_obj = self.env["stock.route"]
        routes = route_obj
        wh_routes = route_obj.search([("supplied_wh_id", "=", wh.id)])
        if product:
            routes += product.mapped("route_ids") | product.mapped("categ_id").mapped(
                "total_route_ids"
            )
        if wh_routes:
            routes |= wh_routes
        parents = self.get_parents(location)
        if type == "send":
            route_ids = (
                routes.mapped("rule_ids")
                .filtered(lambda x: x.propagate_warehouse_id == wh)
                .mapped("route_id")
            )
        else:
            route_ids = routes.filtered(
                lambda r: any(p.location_dest_id in parents for p in r.rule_ids)
            )
        return route_ids

    @api.depends("product_id", "warehouse_id", "location_id")
    def _compute_route_ids(self):
        for row in self:
            for wh in row.mapped("warehouse_id"):
                for record in row.filtered(lambda r: r.warehouse_id == wh):
                    record.route_ids = self._get_routes(
                        wh, record.product_id, row.location_id, row.type
                    )
        return True


class StockPicking(models.Model):
    _inherit = "stock.picking"

    request_id = fields.Many2one("stock.product.request", copy=True)
    route_request = fields.Char("Route Request", copy=True)

    def action_pack_operation_auto_fill(self):
        self.action_assign()
        self._check_action_pack_operation_auto_fill_allowed()
        operations = self.mapped("move_line_ids")
        orig_ids = operations.mapped("move_id.move_orig_ids")
        if not orig_ids:
            return super().action_pack_operation_auto_fill()
        else:
            op_to_auto_fill = operations.filtered(
                lambda op: (
                    op.product_id
                    and not op.lot_id
                    and not op.picking_id.picking_type_id.avoid_lot_assignment
                )
            )
            for op in op_to_auto_fill:
                op.qty_done = sum(
                    orig_ids.filtered(lambda x: x.product_id == op.product_id).mapped(
                        "quantity_done"
                    )
                )
            op_lot_to_auto_fill = operations.filtered(
                lambda op: (
                    op.product_id
                    and op.lot_id
                    and not op.picking_id.picking_type_id.avoid_lot_assignment
                )
            )
            lot_ids = op_lot_to_auto_fill.mapped("lot_id")
            for op in op_lot_to_auto_fill:
                origin_ids = orig_ids.mapped("move_line_ids").filtered(
                    lambda x: x.product_id == op.product_id
                )
                for org in origin_ids:
                    if org.lot_id in lot_ids:
                        if op.lot_id == org.lot_id:
                            op.qty_done = org.qty_done
                            op.product_uom_qty = org.product_uom_qty
                    else:
                        op.copy(
                            {
                                "lot_id": org.lot_id.id,
                                "qty_done": org.qty_done,
                                "product_uom_qty": org.product_uom_qty,
                            }
                        )
        return True


class StockMove(models.Model):
    _inherit = "stock.move"

    request_id = fields.Many2one("stock.product.request", copy=True)
