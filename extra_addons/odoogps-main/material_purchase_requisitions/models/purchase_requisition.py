from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MaterialPurchaseRequisition(models.Model):
    _name = "material.purchase.requisition"
    _description = "Purchase Requisition"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin"]
    _order = "id desc"

    def unlink(self):
        for rec in self:
            if rec.state not in ("draft", "cancel", "reject"):
                raise UserError(
                    _(
                        "You can not delete Purchase Requisition which is not in draft or cancelled or rejected state."
                    )
                )
        return super(MaterialPurchaseRequisition, self).unlink()

    name = fields.Char(
        string="Number",
        index=True,
        readonly=1,
    )
    state = fields.Selection(
        [
            ("draft", "New"),
            ("dept_confirm", "Waiting Department Approval"),
            ("ir_approve", "Waiting IR Approval"),
            ("approve", "Approved"),
            ("stock", "Purchase Order Created"),
            ("receive", "Received"),
            ("cancel", "Cancelled"),
            ("reject", "Rejected"),
        ],
        default="draft",
        tracking=True,
    )
    request_date = fields.Date(
        string="Requisition Date",
        default=fields.Date.today(),
        required=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        required=True,
        copy=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        default=lambda self: self.env["hr.employee"].search(
            [("user_id", "=", self.env.uid)], limit=1
        ),
        required=True,
        copy=True,
    )
    approve_manager_id = fields.Many2one(
        "hr.employee",
        string="Department Manager",
        readonly=True,
        copy=False,
    )
    reject_manager_id = fields.Many2one(
        "hr.employee",
        string="Department Manager Reject",
        readonly=True,
    )
    approve_employee_id = fields.Many2one(
        "hr.employee",
        string="Approved by",
        readonly=True,
        copy=False,
    )
    reject_employee_id = fields.Many2one(
        "hr.employee",
        string="Rejected by",
        readonly=True,
        copy=False,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        copy=True,
    )
    location_id = fields.Many2one(
        "stock.location",
        string="Source Location",
        copy=True,
    )
    requisition_line_ids = fields.One2many(
        "material.purchase.requisition.line",
        "requisition_id",
        string="Purchase Requisitions Line",
        copy=True,
    )
    date_end = fields.Date(
        string="Requisition Deadline",
        readonly=True,
        help="Last date for the product to be needed",
        copy=True,
    )
    date_done = fields.Date(
        string="Date Done",
        readonly=True,
        help="Date of Completion of Purchase Requisition",
    )
    managerapp_date = fields.Date(
        string="Department Approval Date",
        readonly=True,
        copy=False,
    )
    manareject_date = fields.Date(
        string="Department Manager Reject Date",
        readonly=True,
    )
    userreject_date = fields.Date(
        string="Rejected Date",
        readonly=True,
        copy=False,
    )
    userrapp_date = fields.Date(
        string="Approved Date",
        readonly=True,
        copy=False,
    )
    receive_date = fields.Date(
        string="Received Date",
        readonly=True,
        copy=False,
    )
    reason = fields.Text(
        string="Reason for Requisitions",
        required=False,
        copy=True,
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        copy=True,
    )
    dest_location_id = fields.Many2one(
        "stock.location",
        string="Destination Location",
        required=False,
        copy=True,
    )
    delivery_picking_id = fields.Many2one(
        "stock.picking",
        string="Internal Picking",
        readonly=True,
        copy=False,
    )
    requisiton_responsible_id = fields.Many2one(
        "hr.employee",
        string="Requisition Responsible",
        copy=True,
    )
    employee_confirm_id = fields.Many2one(
        "hr.employee",
        string="Confirmed by",
        readonly=True,
        copy=False,
    )
    confirm_date = fields.Date(
        string="Confirmed Date",
        readonly=True,
        copy=False,
    )

    purchase_order_ids = fields.One2many(
        "purchase.order",
        "custom_requisition_id",
        string="Purchase Ordes",
    )
    custom_picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Picking Type",
        copy=False,
    )
    global_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Vendor',
        required=False)

    @api.model
    def create(self, vals):
        name = self.env["ir.sequence"].next_by_code("purchase.requisition.seq")
        vals.update({"name": name})
        res = super(MaterialPurchaseRequisition, self).create(vals)
        return res

    def requisition_confirm(self):
        for rec in self:
            manager_mail_template = self.env.ref(
                "material_purchase_requisitions.email_confirm_material_purchase_requistion"
            )
            rec.employee_confirm_id = rec.employee_id.id
            rec.confirm_date = fields.Date.today()
            rec.state = "dept_confirm"
            if manager_mail_template:
                manager_mail_template.send_mail(self.id)

    def requisition_reject(self):
        for rec in self:
            rec.state = "reject"
            rec.reject_employee_id = self.env["hr.employee"].search(
                [("user_id", "=", self.env.uid)], limit=1
            )
            rec.userreject_date = fields.Date.today()

    def manager_approve(self):
        for rec in self:
            rec.managerapp_date = fields.Date.today()
            rec.approve_manager_id = self.env["hr.employee"].search(
                [("user_id", "=", self.env.uid)], limit=1
            )
            employee_mail_template = self.env.ref(
                "material_purchase_requisitions.email_purchase_requisition_iruser_custom"
            )
            email_iruser_template = self.env.ref(
                "material_purchase_requisitions.email_purchase_requisition"
            )
            employee_mail_template.sudo().send_mail(self.id)
            email_iruser_template.sudo().send_mail(self.id)
            rec.state = "ir_approve"

    def user_approve(self):
        for rec in self:
            rec.userrapp_date = fields.Date.today()
            rec.approve_employee_id = self.env["hr.employee"].search(
                [("user_id", "=", self.env.uid)], limit=1
            )
            rec.state = "approve"

    def reset_draft(self):
        for rec in self:
            rec.state = "draft"

    @api.model
    def _prepare_pick_vals(self, line=False, stock_id=False):
        pick_vals = {
            "product_id": line.product_id.id,
            "product_uom_qty": line.qty,
            "product_uom": line.uom.id,
            "location_id": self.location_id.id,
            "location_dest_id": self.dest_location_id.id,
            "name": line.product_id.name,
            "picking_type_id": self.custom_picking_type_id.id,
            "picking_id": stock_id.id,
            "custom_requisition_line_id": line.id,
            "company_id": line.requisition_id.company_id.id,
        }
        return pick_vals

    @api.model
    def _prepare_po_line(self, line=False, purchase_order=False):
        seller = line.product_id._select_seller(
            partner_id=self._context.get('partner_id'),
            quantity=line.qty,
            date=purchase_order.date_order and purchase_order.date_order.date(),
            uom_id=line.uom
        )
        po_line_vals = {
            'product_id': line.product_id.id,
            'name': line.product_id.name,
            'product_qty': line.qty,
            'product_uom': line.uom.id,
            'date_planned': fields.Date.today(),
            # 'price_unit': line.product_id.standard_price,
            'price_unit': seller.price or line.product_id.standard_price or 0.0,
            'order_id': purchase_order.id,
            # 'account_analytic_id': self.analytic_account_id.id,
            'analytic_distribution': {self.sudo().analytic_account_id.id: 100} if self.analytic_account_id else False,
            'custom_requisition_line_id': line.id
        }
        return po_line_vals

    def request_stock(self):
        stock_obj = self.env["stock.picking"]
        move_obj = self.env["stock.move"]
        purchase_obj = self.env["purchase.order"]
        purchase_line_obj = self.env["purchase.order.line"]
        stock_id = False
        for rec in self:
            if not rec.requisition_line_ids:
                raise UserError(_("Please create some requisition lines."))
            if any(
                    line.requisition_type == "internal" for line in rec.requisition_line_ids
            ):
                if not rec.location_id.id:
                    raise UserError(
                        _("Select Source location under the picking details.")
                    )
                if not rec.custom_picking_type_id.id:
                    raise UserError(_("Select Picking Type under the picking details."))
                if not rec.dest_location_id:
                    raise UserError(
                        _("Select Destination location under the picking details.")
                    )
                picking_vals = {
                    "partner_id": rec.employee_id.sudo().address_home_id.id,
                    "location_id": rec.location_id.id,
                    "location_dest_id": rec.dest_location_id and rec.dest_location_id.id
                                        or rec.employee_id.dest_location_id.id
                                        or rec.employee_id.department_id.dest_location_id.id,
                    "picking_type_id": rec.custom_picking_type_id.id,
                    "note": rec.reason,
                    "custom_requisition_id": rec.id,
                    "origin": rec.name,
                    "company_id": rec.company_id.id,
                }
                stock_id = stock_obj.sudo().create(picking_vals)
                delivery_vals = {
                    "delivery_picking_id": stock_id.id,
                }
                rec.write(delivery_vals)

            po_dict = {}
            requisition_partner = rec.global_partner_id
            for line in rec.requisition_line_ids:
                if line.requisition_type == "internal":
                    pick_vals = rec._prepare_pick_vals(line, stock_id)
                    move_obj.sudo().create(pick_vals)
                if line.requisition_type == "purchase":
                    if not line.partner_id and not requisition_partner:
                        raise UserError(
                            _(
                                "Please enter at least one vendor on Requisition or "
                                "Requisition Lines for Requisition Action Purchase"
                            )
                        )
                    if requisition_partner and not line.partner_id:
                        self._create_purchase_orders(requisition_partner, line, po_dict)
                    for partner in line.partner_id:
                        self._create_purchase_orders(partner, line, po_dict)
                rec.state = "stock"

    def _create_purchase_orders(self, partner, line, po_dict):
        purchase_obj = self.env['purchase.order']
        purchase_line_obj = self.env['purchase.order.line']
        if partner not in po_dict:
            po_vals = {
                "partner_id": partner.id,
                "currency_id": self.env.user.company_id.currency_id.id,
                "date_order": fields.Date.today(),
                "company_id": self.company_id.id,
                "custom_requisition_id": self.id,
                "origin": self.name,
            }
            purchase_order = purchase_obj.create(po_vals)
            po_dict.update({partner: purchase_order})
            po_line_vals = self._prepare_po_line(line, purchase_order)
            purchase_line_obj.sudo().create(po_line_vals)
        else:
            purchase_order = po_dict.get(partner)
            po_line_vals = self._prepare_po_line(line, purchase_order)
            purchase_line_obj.sudo().create(po_line_vals)

    def action_received(self):
        for rec in self:
            rec.receive_date = fields.Date.today()
            rec.state = "receive"

    def action_cancel(self):
        for rec in self:
            rec.state = "cancel"

    @api.onchange("employee_id")
    def set_department(self):
        for rec in self:
            rec.department_id = rec.employee_id.sudo().department_id.id
            rec.dest_location_id = (
                    rec.employee_id.sudo().dest_location_id.id
                    or rec.employee_id.sudo().department_id.dest_location_id.id
            )

    def show_picking(self):
        res = False
        for rec in self:
            res = self.env.ref("stock.action_picking_tree_all")
            res = res.sudo().read()[0]
            res["domain"] = str([("custom_requisition_id", "=", rec.id)])
        return res

    def action_show_po(self):
        for rec in self:
            purchase_action = self.env.ref("purchase.purchase_rfq")
            purchase_action = purchase_action.sudo().read()[0]
            purchase_action["domain"] = str([("custom_requisition_id", "=", rec.id)])
        return purchase_action