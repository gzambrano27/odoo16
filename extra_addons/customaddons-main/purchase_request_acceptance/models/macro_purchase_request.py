# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

class MacroPurchaseRequest(models.Model):
    _inherit = "macro.purchase.request"

    pr_count = fields.Integer(compute="_compute_pr_ids", string="PR count", default=0)
    pr_ids = fields.One2many(
        comodel_name="request.acceptance",
        compute="_compute_pr_ids",
        string="Request Acceptances",
    )
    pr_line_ids = fields.One2many(
        comodel_name="request.acceptance.line",
        inverse_name="purchase_line_id",
        string="PR Lines",
        readonly=True,
    )
    pr_accepted = fields.Boolean(
        string="PR Accepted",
        compute="_compute_pr_accepted",
        search="_search_pr_accepted",
    )

    @api.depends("pr_line_ids")
    def _compute_pr_ids(self):
        for order in self:
            order.pr_ids = (
                order.mapped("line_ids").mapped("pr_line_ids").mapped("pr_id")
            )
            order.pr_count = len(order.pr_ids)
    
    def action_view_pr(self):
        self.ensure_one()
        act = self.env.ref("purchase_request_acceptance.action_request_acceptance")
        result = act.sudo().read()[0]
        create_pr = self.env.context.get("create_pr", False)
        result["context"] = {
            "default_request_id": self.id,
            "default_request_type": self.request_type,
            "default_company_id": self.company_id.id,
            "default_currency_id": self.currency_id.id,
            "default_date_due": self.date_planned,
            "default_picking_type_id": self.picking_type_id.id,
            "default_analytic_distribution": self.analytic_distribution,
            "default_pr_line_ids": [
                Command.create(
                    {
                        "purchase_line_id": line.id,
                        "name": line.name,
                        "product_uom": line.product_id.uom_id.id,
                        "product_id": line.product_id.id,
                        "tipo_costo": line.tipo_costo,
                        "rubro": line.rubro,
                        "product_qty": line._get_product_qty(),
                        "analytic_distribution": line.analytic_distribution,
                        "costo_uni_apu":line.costo_unit_apu
                    }
                )
                for line in self.line_ids
                if line._get_product_qty() != 0
            ],
        }
        if len(self.pr_ids) > 1 and not create_pr:
            result["domain"] = "[('id', 'in', " + str(self.pr_ids.ids) + ")]"
        else:
            res = self.env.ref(
                "purchase_request_acceptance.view_request_acceptance_form", False
            )
            result["views"] = [(res and res.id or False, "form")]
            if not create_pr:
                result["res_id"] = self.pr_ids.id or False
        return result

    
    def _compute_pr_accepted(self):
        for order in self:
            lines = order.line_ids.filtered(
                lambda l: l.product_qty > 0 and l.qty_to_accept > 0
            )
            order.pr_accepted = not any(lines)

    @api.model
    def _search_pr_accepted(self, operator, value):
        if operator not in ["=", "!="] or not isinstance(value, bool):
            raise UserError(_("Operation not supported"))
        recs = self.search([]).filtered(lambda l: l.pr_accepted is value)
        return [("id", "in", recs.ids)]

    def action_open_generate_pr_wizard(self):
        self.ensure_one()

        # Crear el wizard sin líneas primero
        wizard = self.env['wizard.generate.pr'].create({
            'request_id': self.id,
        })

        # Agregar las líneas una por una manualmente (sin depender de onchange)
        for line in self.line_ids.filtered(lambda l: l.product_qty > 0 and not l.cancelled):
            self.env['wizard.generate.pr.line'].create({
                'wizard_id': wizard.id,
                'original_line_id': line.id,
                'product_id': line.product_id.id,
                'product_uom_id': line.product_uom_id.id,
                'quantity_requested': line.product_qty,
                'quantity_to_accept': line.product_qty,
                'analytic_distribution': line.analytic_distribution,
                'tipo_costo': line.tipo_costo,
                'rubro': line.rubro,
                'costo_uni_apu':line.costo_uni_apu
            })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.generate.pr',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }


class MacroPurchaseRequestLine(models.Model):
    _inherit = "macro.purchase.request.line"

    pr_line_ids = fields.One2many(
        comodel_name="request.acceptance.line",
        inverse_name="purchase_line_id",
        string="PR Lines",
        readonly=True,
    )
    qty_accepted = fields.Float(
        compute="_compute_qty_accepted",
        string="Accepted Qty.",
        store=True,
        readonly=True,
        digits="Product Unit of Measure",
    )
    qty_to_accept = fields.Float(
        compute="_compute_qty_accepted",
        string="To Accept Qty.",
        store=True,
        readonly=True,
        digits="Product Unit of Measure",
    )

    @api.constrains('qty_accepted', 'product_qty')
    def _check_aceptado(self):
        for line in self:
            if line.qty_accepted > line.product_qty:
                #print('a')
                raise ValidationError(
                    _("La cantidad aceptada %s no puede ser mayor que la cantidad del pedido %s") %
                    (line.qty_accepted, line.product_qty)
                )

    @api.onchange('qty_accepted')
    def _onchange_aceptado(self):
        for line in self:
            line.qty_received = line.qty_accepted

    def _get_product_qty(self):
        return self.product_qty - sum(
            pr_line.product_qty
            for pr_line in self.pr_line_ids
            if pr_line.pr_id.state != "cancel"
        )

    @api.depends(
        "pr_line_ids.pr_id.state",
        "pr_line_ids.product_qty",
        "product_qty",
        "request_id.state",
    )
    def _compute_qty_accepted(self):
        for line in self:
            qty_accepted = sum(
                pr_line.product_uom._compute_quantity(
                    pr_line.product_qty, line.product_uom_id, round=False
                )
                for pr_line in line.pr_line_ids.filtered(lambda l: l.pr_id.state == "accept")
            )
            line.qty_accepted = qty_accepted
            line.qty_to_accept = line.product_qty - qty_accepted
