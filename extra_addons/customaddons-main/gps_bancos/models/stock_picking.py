# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID



class StockPicking(models.Model):
    _inherit = "stock.picking"

    payment_request_ids = fields.One2many("account.payment.request", "picking_id", string="Solicitudes de Pago")
    # currency_id=fields.Many2one(related="company_id.currency_id",store=False,string="Moneda",readonly=True)
    # po_received_subtotal = fields.Monetary(
    #     string="Subtotal OC(Recibido)",
    #     compute="_compute_po_received_amounts",
    #     currency_field="currency_id",
    #     store=False
    # )
    # po_received_tax = fields.Monetary(
    #     string="IVA OC(Recibido)",
    #     compute="_compute_po_received_amounts",
    #     currency_field="currency_id",
    #     store=False
    # )
    # po_received_total = fields.Monetary(
    #     string="Total OC(Recibido)",
    #     compute="_compute_po_received_amounts",
    #     currency_field="currency_id",
    #     store=False
    # )
    #
    # @api.depends("move_ids_without_package", "move_ids_without_package.quantity_done")
    # @api.onchange("move_ids_without_package", "move_ids_without_package.quantity_done")
    # def _compute_po_received_amounts(self):
    #     for picking in self:
    #         subtotal = 0.0
    #         tax_total = 0.0
    #         currency = picking.company_id.currency_id
    #
    #         for move in picking.move_ids_without_package:
    #             po_line = move.purchase_line_id
    #             if not po_line:
    #                 continue
    #
    #             qty = move.quantity_done
    #             if qty <= 0:
    #                 continue
    #
    #             # Subtotal = precio * cantidad
    #             line_subtotal = po_line.price_unit * qty
    #             subtotal += line_subtotal
    #
    #             # Calcular impuestos
    #             taxes_res = po_line.taxes_id.compute_all(
    #                 po_line.price_unit,
    #                 currency,
    #                 qty,
    #                 product=po_line.product_id,
    #                 partner=po_line.order_id.partner_id,
    #             )
    #             tax_total += sum(t["amount"] for t in taxes_res.get("taxes", []))
    #
    #         picking.po_received_subtotal = subtotal
    #         picking.po_received_tax = tax_total
    #         picking.po_received_total = subtotal + tax_total

