from odoo import fields, models, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    purchase_order_type = fields.Selection(
        [("service", "Servicio"), ("product", "Producto"), ("mixed", "Producto y Servicio")],
        string="Tipo de Orden de Compra",
        default="product",
        compute="_compute_purchase_order_type",
        store=True,
    )

    @api.depends("order_line.product_id.type")
    def _compute_purchase_order_type(self):
        for rec in self:
            if all([line.product_id.type == "service" for line in rec.order_line]):
                rec.purchase_order_type = "service"
            elif all([line.product_id.type in ("product", "consu") for line in rec.order_line]):
                rec.purchase_order_type = "product"
            else:
                rec.purchase_order_type = "mixed"

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        message = ""
        for rec in self:
            if not rec.partner_id.country_id:
                message += (
                    "El proveedor no tiene país asignado en la Orden  %s\n" % rec.name
                )
            if not rec.partner_id.street:
                message += (
                    "El proveedor no tiene dirección asignada en la Orden  %s\n"
                    % rec.name
                )
            if not rec.partner_id.l10n_latam_identification_type_id:
                message += (
                    "El proveedor no tiene tipo de identificación asignado en la Orden  %s\n"
                    % rec.name
                )
            if not rec.partner_id.l10n_ec_payment_id:
                message += (
                    "El proveedor no tiene forma de pago asignada en la Orden  %s\n"
                    % rec.name
                )
            if not rec.partner_id.mobile:
                message += (
                    "El proveedor no tiene teléfono asignado en la Orden  %s\n"
                    % rec.name
                )
            if not rec.partner_id.email:
                message += (
                    "El proveedor no tiene correo asignado en la Orden  %s\n" % rec.name
                )
            if not rec.partner_id.vat:
                message += (
                    "El proveedor no tiene RUC asignado en la Orden  %s\n" % rec.name
                )
            if not rec.partner_id.property_account_position_id:
                message += (
                    "El proveedor no tiene posición fiscal asignada en la Orden  %s\n"
                    % rec.name
                )
            if not rec.payment_term_id:
                message += (
                        "La Orden  %s\n no tiene plazo de pago asignada"
                        % rec.name
                )
        if message:
            raise UserError(_(message))
        return res
