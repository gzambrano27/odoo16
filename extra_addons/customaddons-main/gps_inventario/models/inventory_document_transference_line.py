# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError

class InventoryDocumentTransferenceLine(models.Model):
    _name = "inventory.document.transference.line"
    _description = "Detalle de Documento de Transferencia Inventario"
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]

    document_id = fields.Many2one("inventory.document.transference", "Documento", ondelete="cascade")
    name = fields.Char("Descripcion", required=True)
    product_id = fields.Many2one("product.product", "Producto", domain=[('detailed_type', '=', 'product')])
    stock = fields.Float("Stock", default=0)
    quantity = fields.Float("Cantidad Pedida", default=0)
    quantity_delivery = fields.Float("Cantidad Entregada", default=0)
    pending_quantity = fields.Float("Cantidad Pendiente", compute="_compute_pending_quantity", store=True)
    comments = fields.Text("Observaciones")
    to_stock = fields.Float("Stock Destino", default=0)

    @api.depends('quantity', 'quantity_delivery')
    def _compute_pending_quantity(self):
        for line in self:
            line.pending_quantity = max(0.0, line.quantity - line.quantity_delivery)

    @api.onchange('comments')
    def onchange_comments(self):
        self.comments = self.comments.upper() if self.comments else None

    @api.onchange("product_id")
    def onchange_product_id(self):
        if not self.product_id:
            self.name = None
            self.stock = 0
            self.to_stock = 0
            return
        self.name = self.product_id.name
        self.update_stock()

    def update_stock(self):
        sup = self.env["res.users"].browse(SUPERUSER_ID)
        OBJ_QUANT = self.env["stock.quant"].sudo().with_user(sup)
        self.ensure_one()
        stock = 0
        to_stock = 0

        if self.document_id.stock_location_id:
            srch_quant = OBJ_QUANT.search([
                ('product_id', '=', self.product_id.id),
                ('location_id', '=', self.document_id.stock_location_id.id)
            ])
            if srch_quant:
                stock = srch_quant[0].quantity

        if self.document_id.to_stock_location_id:
            srch_quant = OBJ_QUANT.search([
                ('product_id', '=', self.product_id.id),
                ('location_id', '=', self.document_id.to_stock_location_id.id)
            ])
            if srch_quant:
                to_stock = srch_quant[0].quantity

        self.to_stock = to_stock
        self.stock = stock

    @api.constrains('analytic_distribution')
    def _check_analytic_distribution(self):
        for record in self:
            if not record.analytic_distribution:
                raise UserError(_(
                    "No puedes crear o modificar una movimiento sin haber ingresado la distribucion analítica, para el producto '%s'.",
                    record.product_id.default_code))