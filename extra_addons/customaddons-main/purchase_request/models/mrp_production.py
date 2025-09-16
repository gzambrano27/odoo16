from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    
    purchase_request_ids = fields.One2many(
        "purchase.request", "mrp_production_id", string="Requisitions"
    )
    purchase_request_count = fields.Integer(
        compute="_compute_requisition_count", string="Requisitions"
    )

    def _compute_requisition_count(self):
        for record in self:
            record.purchase_request_count = len(record.purchase_request_ids)

    def action_view_purchase_request(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Requisiciones de Material",
            "res_model": "purchase.request",
            "view_mode": "tree,form",
            "domain": [("mrp_production_id", "=", self.id)],
            "context": {"create": False},
        }

    def create_purchase_request(self):
        self.ensure_one()
        if self.state in ("cancel", "done"):
            raise UserError(_("You cannot create a purchase request for a cancelled or done manufacturing order."))

        if not self.assembly_responsible or not self.equipment_responsible:
            raise UserError(_("Debes especificar un responsable de armado y de equipo para crear una requisicion de materiales!!."))

        # Encabezado de la solicitud
        picking_type = self.env['stock.picking.type'].search([('barcode', 'like',  f"%RECEIP%"),('warehouse_id','=',self.picking_type_id.warehouse_id.id),('code','=','incoming')], limit=1)
        values = {
            "requested_by": self.assembly_responsible.user_id.id,
            "assigned_to": self.equipment_responsible.user_id.id,
            "date_planned": self.date_planned_start.date(),
            "origin": self.name,
            "mrp_production_id": self.id,
            "company_id": self.company_id.id,
            "picking_type_id": picking_type.id,
            "analytic_distribution":{str(self.analytic_account_id.id): 100}  if self.analytic_account_id else False,
        }

        # Crear líneas de la solicitud
        lines = []
        for line in self.move_raw_ids:
            if not line.product_id or line.product_uom_qty <= 0:
                continue
            lines.append((0, 0, {
                "product_id": line.product_id.id,
                "product_qty": line.product_uom_qty,
                "product_uom_id": line.product_uom.id,
                "date_required": self.date_planned_start.date(),
                "specifications": line.name,
                "analytic_distribution": {str(self.analytic_account_id.id): 100}  if self.analytic_account_id else False,
            }))

        if not lines:
            raise UserError(_("There are no products to include in the purchase request."))

        values["line_ids"] = lines

        # Crear la solicitud
        purchase_request = self.env["purchase.request"].create(values)

        return {
            "type": "ir.actions.act_window",
            "name": _("Purchase Request"),
            "res_model": "purchase.request",
            "view_mode": "form",
            "res_id": purchase_request.id,
        }
