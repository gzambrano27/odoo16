# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import base64
import xlsxwriter
import io
import json

_STATES = [
    ("draft", "Draft"),
    ("to_approve", "To be approved"),
    ("approved", "Approved"),
    ("in_progress", "In progress"),
    ("done", "Done"),
    ("rejected", "Rejected"),
]
_STATESREV = [
    ("revisado", "Revisado Supply"),
    ("no revisado", "No Revisado Supply")
]

class MacroPurchaseRequest(models.Model):

    _name = "macro.purchase.request"
    _description = "Macro Purchase Request"
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _order = 'priority desc, id desc'

    @api.model
    def _company_get(self):
        return self.env["res.company"].browse(self.env.company.id)

    @api.model
    def _get_default_requested_by(self):
        return self.env["res.users"].browse(self.env.uid)

    @api.model
    def _get_default_name(self):
        return self.env["ir.sequence"].next_by_code("macro.purchase.request.seq")

    @api.model
    def _default_picking_type(self):
        type_obj = self.env["stock.picking.type"]
        company_id = self.env.context.get("company_id") or self.env.company.id
        types = type_obj.search(
            [("code", "=", "incoming"), ("warehouse_id.company_id", "=", company_id)]
        )
        if not types:
            types = type_obj.search(
                [("code", "=", "incoming"), ("warehouse_id", "=", False)]
            )
        return types[:1]

    @api.depends("state")
    def _compute_is_editable(self):
        for rec in self:
            if rec.state in (
                "to_approve",
                "approved",
                "rejected",
                "in_progress",
                "done",
            ):
                rec.is_editable = False
            else:
                rec.is_editable = True

    name = fields.Char(
        string="Request Reference",
        required=True,
        default=lambda self: _("New"),
        tracking=True,
    )
    is_name_editable = fields.Boolean(
        default= False #lambda self: self.env.user.has_group("base.group_no_one"),
    )
    origin = fields.Char(string="Source Document")
    date_start = fields.Date(
        string="Creation date",
        help="Date when the user initiated the request.",
        default=fields.Date.context_today,
        tracking=True,
    )
    requested_by = fields.Many2one(
        comodel_name="res.users",
        required=True,
        copy=False,
        tracking=True,
        default=_get_default_requested_by,
        index=True,
    )
    assigned_to = fields.Many2one(
        comodel_name="res.users",
        string="Approver",
        tracking=True,
        index=True,
    )
    description = fields.Text()
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=False,
        default=_company_get,
        tracking=True,
    )
    line_ids = fields.One2many(
        comodel_name="macro.purchase.request.line",
        inverse_name="request_id",
        string="Products to Purchase",
        readonly=True,
        copy=True,
        tracking=True,
        states={"draft": [("readonly", False)]},
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        related="line_ids.product_id",
        string="Product",
        readonly=True,
    )
    state = fields.Selection(
        selection=_STATES,
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        default="draft",
    )

    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Picking Type",
        required=True,
        default=_default_picking_type,
    )
    group_id = fields.Many2one(
        comodel_name="procurement.group",
        string="Procurement Group",
        copy=False,
        index=True,
    )
    
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    
    date_planned = fields.Date(
        string="Fecha Llegada",
        default=lambda self: fields.Date.to_string(datetime.today() + timedelta(days=15)),#fields.Date.context_today,
        tracking=True,
    )
    estado_revision = fields.Selection(
        selection=_STATESREV,
        string="Estado Revision Supply",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        default="no revisado",
    )
    show_estado_revision = fields.Boolean(compute='_compute_show_estado_revision')
    sale_order_id = fields.Many2one('sale.order', string='Presupuesto', help="Asocia esta requisición de compra con un pedido de venta",)
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'Urgent')], 'Priority', default='0', index=True)
    
    request_type = fields.Selection(
        [("service", "Servicio"), ("product", "Producto"), ("mixed", "Producto y Servicio")],
        string="Tipo de Requisicion",
        default="product",
        compute="_compute_request_type",
        store=True,
    )
    permite_aprobar = fields.Boolean(string="¿Permite aprobar?", default=False)
    to_approve_allowed = fields.Boolean(compute="_compute_to_approve_allowed")
    analytic_distribution = fields.Json(
        string="Analitica",
        default={},
        help="Distribucion analitica que se aplicara a todas las lineas",
    )
    superintendente = fields.Many2one('res.users', 'Superintendente')
    supervisor = fields.Many2one('res.users', 'Supervisor')

    @api.depends("state", "line_ids.product_qty", "line_ids.cancelled")
    def _compute_to_approve_allowed(self):
        for rec in self:
            if rec.state == "draft":
                for line in rec.line_ids:
                    if not line.cancelled and line.product_qty >= 0:
                        if line.product_qty <= 0 and line.product_id:
                            raise UserError(_("Coloque la cantidad al producto '%s'.", line.product_id.default_code))
                rec.to_approve_allowed = True
            else:
                rec.to_approve_allowed = False

    @api.depends("line_ids.product_id.detailed_type")
    def _compute_request_type(self):
        for rec in self:
            if all([line.product_id.detailed_type in ("service", "consu") for line in rec.line_ids]):
                rec.request_type = "service"
            elif all([line.product_id.detailed_type == "product" for line in rec.line_ids]):
                rec.request_type = "product"
            else:
                rec.request_type = "mixed"

    @api.depends('state')
    def _compute_show_estado_revision(self):
        for rec in self:
            rec.show_estado_revision = rec.state == 'approved'



   
    def action_view_stock_picking(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock.action_picking_tree_all"
        )
        # remove default filters
        action["context"] = {}
        lines = self.mapped(
            "line_ids.purchase_request_allocation_ids.stock_move_id.picking_id"
        )
        if len(lines) > 1:
            action["domain"] = [("id", "in", lines.ids)]
        elif lines:
            action["views"] = [(self.env.ref("stock.view_picking_form").id, "form")]
            action["res_id"] = lines.id
        return action

    @api.model
    def _get_partner_id(self, request):
        user_id = request.assigned_to or self.env.user
        return user_id.partner_id.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self._get_default_name()
        requests = super(MacroPurchaseRequest, self).create(vals_list)

        for line in requests.line_ids:
            if not line.cancelled and line.product_qty >= 0:
                if line.product_qty <= 0 and line.product_id:
                    raise UserError(_("Coloque la cantidad al producto '%s'.", line.product_id.default_code))
                if line.product_id.categ_id.asset_fixed_control or line.product_id.categ_id.asset_fixed_depreciable:
                    if line.un_solo_custodio and (len(line.employees_ids.ids) != 1):
                        raise UserError(_("El producto '%s' es un activo fijo e indica que debe tener asignado un solo empleado, asegurese de hacerlo", line.product_id.default_code))
                    elif not line.un_solo_custodio and not (len(line.employees_ids.ids) == int(line.product_qty)):
                        raise UserError(_("El producto '%s' es un activo fijo y debe ser asignado a la misma cantidad de empleados.", line.product_id.default_code))
                else:
                    if (len(line.employees_ids.ids) > 0):
                        raise UserError(_("El producto '%s'. No es un activo fijo por lo tanto no debe de ser asignado a empleados.", line.product_id.default_code))

        for vals, request in zip(vals_list, requests):
            if vals.get("assigned_to"):
                partner_id = self._get_partner_id(request)
                request.message_subscribe(partner_ids=[partner_id])
        return requests

    def write(self, vals):
        if 'estado_revision' in vals:
            user_group_ids = self.env.user.groups_id.ids
            group_supply = self.env.ref('purchase_request.group_purchase_request_supply')
            group_manager = self.env.ref('purchase_request.group_purchase_request_manager')
            
            # Solo si está en supply y NO está en manager (sin herencia)
            if group_supply.id in user_group_ids and group_manager.id not in user_group_ids:
                pass  # permitido
            else:
                raise UserError("Solo los usuarios del grupo Supply, pueden modificar este campo.")
        res = super(MacroPurchaseRequest, self).write(vals)
        for request in self:
            if vals.get("assigned_to"):
                partner_id = self._get_partner_id(request)
                request.message_subscribe(partner_ids=[partner_id])
        return res

    def _can_be_deleted(self):
        self.ensure_one()
        return self.state == "draft"

    def unlink(self):
        for request in self:
            if not request._can_be_deleted():
                raise UserError(
                    _("You cannot delete a purchase request which is not draft.")
                )
        return super(MacroPurchaseRequest, self).unlink()

    def button_draft(self):
        self.mapped("line_ids").do_uncancel()
        return self.write({"state": "draft"})

    def button_to_approve(self):
        self.to_approve_allowed_check()
        return self.write({"state": "to_approve"})

    def button_approved(self):
        return self.write({"state": "approved"})

    def button_rejected(self):
        self.mapped("line_ids").do_cancel()
        return self.write({"state": "rejected"})

    def button_in_progress(self):
        return self.write({"state": "in_progress"})

    def button_done(self):
        return self.write({"state": "done"})

    def check_auto_reject(self):
        """When all lines are cancelled the purchase request should be
        auto-rejected."""
        for pr in self:
            if not pr.line_ids.filtered(lambda l: l.cancelled is False):
                pr.write({"state": "rejected"})

    def to_approve_allowed_check(self):
        for rec in self:
            print('a')
            # if not rec.to_approve_allowed:
            #     raise UserError(
            #         _(
            #             "You can't request an approval for a purchase request "
            #             "which is empty. (%s)"
            #         )
            #         % rec.name
            #     )