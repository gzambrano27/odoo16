from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PaymentRequestRecalcWizard(models.TransientModel):
    _name = "payment.request.recalc.wizard"
    _description = "Generar Solicitudes de Pago por Recepción/Aceptación"

    purchase_id = fields.Many2one(
        "purchase.order",
        string="Orden de Compra",
        required=True,
        default=lambda self: self.env.context.get("active_id"),
    )
    partner_id = fields.Many2one(related="purchase_id.partner_id", string="Proveedor", readonly=True)
    amount_total = fields.Monetary(related="purchase_id.amount_total", string="Monto OC", readonly=True)
    currency_id = fields.Many2one(related="purchase_id.currency_id")

    picking_ids = fields.Many2many(
        "stock.picking",
        "wiz_picking_rel",
        "wiz_id",
        "picking_id",
        string="Recepciones pendientes",
        store=True,
        domain="[('purchase_id','=',purchase_id),('state','=','done'),('payment_request_ids','=',False)]",
    )

    work_acceptance_ids = fields.Many2many(
        "work.acceptance",
        "wiz_acceptance_rel",
        "wiz_id",
        "acceptance_id",
        string="Aceptaciones pendientes",
        store=True,
        domain="[('purchase_id','=',purchase_id),('state','=','accept'),('payment_request_ids','=',False)]",
    )

    payment_request_ids = fields.Many2many(
        "account.payment.request",
        "wiz_payment_request_rel",  # tabla rel ficticia, requerida por Many2many
        "wiz_id",
        "request_id",
        string="Solicitudes de Pago",
        store=False,
        compute="_compute_payment_request_ids",
        domain="[('order_id','=',purchase_id)]",
    )

    @api.depends("purchase_id")
    @api.onchange("purchase_id")
    def _compute_payment_request_ids(self):
        for wizard in self:
            if wizard.purchase_id:
                wizard.payment_request_ids = wizard.purchase_id.payment_request_ids.ids
            else:
                wizard.payment_request_ids = [(5, 0, 0)]

    def action_generate_requests(self):
        """Crea una solicitud de pago por cada picking o aceptación seleccionada"""
        self.ensure_one()
        po = self.purchase_id
        PaymentRequest = self.env["account.payment.request"]

        # secuencia de cuotas
        quota = len(po.payment_request_ids) + 1

        # procesar aceptaciones
        for wa in self.work_acceptance_ids:
            PaymentRequest.create({
                "company_id": po.company_id.id,
                "order_id": po.id,
                "payment_term_id": po.payment_term_id.id if po.payment_term_id else False,
                "quota": quota,
                "date_maturity": wa.date_receive or fields.Date.context_today(self),
                "partner_id": po.partner_id.id,
                "amount": wa.amount_total,
                "amount_original": wa.amount_total,
                "state": "draft",
                "type": "purchase.order",
                "manual_type": "purchase.order",
                "description_motive": _("CUOTA %s DE %s (Aceptación %s)") % (quota, po.name, wa.name),
                "request_type_id": self.env.ref("gps_bancos.req_type_anticipo_oc").id,
                "percentage": (po.amount_total > 0) and (wa.amount_total / po.amount_total) * 100 or 0.0,
                "document_ref": wa.name,
                "date": wa.date_receive or fields.Date.context_today(self),
                "is_prepayment": False,
            })
            wa.payment_request_id = True  # marcar como procesada
            quota += 1

        # procesar recepciones
        for picking in self.picking_ids:
            PaymentRequest.create({
                "company_id": po.company_id.id,
                "order_id": po.id,
                "payment_term_id": po.payment_term_id.id if po.payment_term_id else False,
                "quota": quota,
                "date_maturity": picking.scheduled_date or fields.Date.context_today(self),
                "partner_id": po.partner_id.id,
                "amount": getattr(picking, "amount_total", 0.0),
                "amount_original": getattr(picking, "amount_total", 0.0),
                "state": "draft",
                "type": "purchase.order",
                "manual_type": "purchase.order",
                "description_motive": _("CUOTA %s DE %s (Recepción %s)") % (quota, po.name, picking.name),
                "request_type_id": self.env.ref("gps_bancos.req_type_anticipo_oc").id,
                "percentage": (po.amount_total > 0) and (getattr(picking, "amount_total", 0.0) / po.amount_total) * 100 or 0.0,
                "document_ref": picking.name,
                "date": picking.scheduled_date or fields.Date.context_today(self),
                "is_prepayment": False,
            })
            picking.payment_request_id = True  # marcar como procesado
            quota += 1

        return {"type": "ir.actions.act_window_close"}
