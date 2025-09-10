from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = "mrp.production"
    _description = "Custom fields for gps"

    assembly_responsible = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        default=lambda self: self.env["hr.employee"].search(
            [("user_id", "=", self.env.uid)], limit=1
        ),
        copy=True,
    )
    equipment_responsible = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        default=lambda self: self.env["hr.employee"].search(
            [("user_id", "=", self.env.uid)], limit=1
        ),
        copy=True,
    )
    force_responsible = fields.Char(string="Force responsible", required=False)
    control_responsible = fields.Char(string="Control responsible", required=False)
    requisition_ids = fields.One2many(
        "material.purchase.requisition", "mrp_production_id", string="Requisitions"
    )
    requisition_count = fields.Integer(
        compute="_compute_requisition_count", string="Requisitions"
    )

    def _compute_requisition_count(self):
        for record in self:
            record.requisition_count = len(record.requisition_ids)

    def action_view_requisitions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Requisitions",
            "res_model": "material.purchase.requisition",
            "view_mode": "tree,form",
            "domain": [("mrp_production_id", "=", self.id)],
            "context": {"create": False},
        }

    def create_requisition_purchase(self):
        self.ensure_one()
        if self.state in ("cancel", "done"):
            raise UserError(
                _(
                    "You cannot create a purchase requisition for a cancelled or done manufacturing order."
                )
            )
        if not self.assembly_responsible or not self.equipment_responsible:
            raise UserError(
                _(
                    "You must specify the assembly and equipment responsible before creating a purchase requisition."
                )
            )
        values = {
            "employee_id": self.assembly_responsible.id,
            "department_id": self.equipment_responsible.id,
            "receive_date": self.date_planned_start.date(),
            "analytic_account_id": self.analytic_account_id.id,
            "mrp_production_id": self.id,
        }
        lines = []
        for line in self.move_raw_ids:
            lines.append(
                (
                    0,
                    0,
                    {
                        "requisition_type": "purchase",
                        "product_id": line.product_id.id,
                        "description": line.product_id.display_name,
                        "qty": line.product_uom_qty,
                        "uom": line.product_uom.id,
                    },
                )
            )
        if not lines:
            raise UserError(
                _("There are no products to purchase for this manufacturing order.")
            )
        values["requisition_line_ids"] = lines
        requisition = self.env["material.purchase.requisition"]
        requisition.create(values)
        return {
            "type": "ir.actions.act_window",
            "name": "Requisitions",
            "res_model": "material.purchase.requisition",
            "view_mode": "tree,form",
            "domain": [("mrp_production_id", "=", self.id)],
            "context": {"create": False},
        }
