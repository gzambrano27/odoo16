# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID



class WorkAcceptance(models.Model):
    _inherit = "work.acceptance"

    # subtotal = fields.Monetary(
    #     string="Subtotal",
    #     compute="_compute_totals",
    #     currency_field="currency_id",
    #     store=False
    # )
    # tax_total = fields.Monetary(
    #     string="IVA",
    #     compute="_compute_totals",
    #     currency_field="currency_id",
    #     store=False
    # )
    # total = fields.Monetary(
    #     string="Total",
    #     compute="_compute_totals",
    #     currency_field="currency_id",
    #     store=False
    # )
    #
    # #@api.depends("line_ids.qty_accepted", "line_ids.price_unit", "line_ids.taxes_id")
    # def _compute_totals(self):
    #     for rec in self:
    #         subtotal = 0.0
    #         tax_total = 0.0
    #         currency = rec.currency_id or rec.company_id.currency_id
    #
    #         for line in rec.line_ids:
    #             qty = line.qty_accepted or 0.0
    #             if qty <= 0:
    #                 continue
    #
    #             # subtotal por línea
    #             line_subtotal = line.price_unit * qty
    #             subtotal += line_subtotal
    #
    #             # calcular impuestos de la línea
    #             taxes_res = line.taxes_id.compute_all(
    #                 line.price_unit,
    #                 currency,
    #                 qty,
    #                 product=line.product_id,
    #                 partner=rec.partner_id,
    #             )
    #             tax_total += sum(t["amount"] for t in taxes_res.get("taxes", []))
    #
    #         rec.subtotal = subtotal
    #         rec.tax_total = tax_total
    #         rec.total = subtotal + tax_total
    #
    # currency_id = fields.Many2one(
    #     related="company_id.currency_id",
    #   store=False,readonly=True
    # )

    payment_request_ids = fields.One2many("account.payment.request", "work_acceptance_id", string="Solicitudes de Pago")

    # @api.depends("wa_line_ids.price_subtotal")
    # def _compute_amount_total(self):
    #     for rec in self:
    #         rec.amount_total = sum(line.price_subtotal for line in rec.wa_line_ids)
    #
    # def button_accept2(self, force=False):
    #     """Al confirmar la aceptación, crea/ajusta las solicitudes de pago"""
    #     res = super().button_accept(force=force)
    #     if not self.env.context.get("manual_date_accept"):
    #         DEC = 2
    #         OBJ_CONFIG = self.env["account.configuration.payment"].sudo()
    #         TODAY = fields.Date.context_today(self)
    #
    #         for acceptance in self:
    #             brw_conf = OBJ_CONFIG.search([
    #                 ('company_id', '=', acceptance.company_id.id)
    #             ])
    #             if not brw_conf:
    #                 raise ValidationError(_("No hay configuración para la empresa %s") % (acceptance.company_id.name,))
    #             po = acceptance.purchase_id
    #             if not po:
    #                 continue
    #
    #             # monto y porcentaje respecto a la PO
    #             amount = acceptance.amount_total
    #             percentage = (
    #                     (po.amount_total > 0)
    #                     and (acceptance.amount_total / po.amount_total) * 100
    #                     or 0.0
    #             )
    #
    #             # solicitudes de la PO
    #             requests = po.payment_request_ids.filtered(
    #                 lambda r: r.type == "purchase.order"
    #             ).sorted("quota")
    #
    #             quota = 1
    #             total = 0.0
    #             updated = False
    #             handled_requests = self.env["account.payment.request"]
    #
    #             for req in requests:
    #                 # --- si ya está pagada, no se toca ---
    #                 if req.state == "done":
    #                     total += req.amount
    #                     handled_requests |= req
    #                     quota = req.quota + 1
    #                     continue
    #
    #                 # --- si está en open ---
    #                 if req.state == "open":
    #                     if req.macro_paid > 0 or req.checked:
    #                         # no se puede alterar
    #                         total += req.amount
    #                         handled_requests |= req
    #                         quota = req.quota + 1
    #                         continue
    #                     else:
    #                         # se puede recalcular
    #                         req.write({
    #                             "quota": quota,
    #                             "date_maturity": acceptance.date_receive,
    #                             "amount": amount,
    #                             "amount_original": amount,
    #                             "description_motive": _("CUOTA %s DE %s") % (quota, po.name),
    #                             "percentage": percentage,
    #                             "document_ref": acceptance.name,
    #                             "date": acceptance.date_receive,
    #                             'type_document':'work_acceptance',
    #                             'work_acceptance_id':acceptance.id
    #                         })
    #                         updated = True
    #                         total += amount
    #                         handled_requests |= req
    #                         quota += 1
    #                         continue
    #
    #                 # --- si está en draft o cancelled ---
    #                 if req.state in ("draft", "cancelled"):
    #                     if req.state == "cancelled":
    #                         req.action_draft()
    #                     req.write({
    #                         "quota": quota,
    #                         "date_maturity": acceptance.date_receive,
    #                         "amount": amount,
    #                         "amount_original": amount,
    #                         "description_motive": _("CUOTA %s DE %s") % (quota, po.name),
    #                         "percentage": percentage,
    #                         "document_ref": acceptance.name,
    #                         "date": acceptance.date_receive,
    #                         'type_document':'work_acceptance',
    #                         'work_acceptance_id':acceptance.id
    #                     })
    #                     updated = True
    #                     total += amount
    #                     handled_requests |= req
    #                     quota += 1
    #
    #             # si no actualizó ninguna cuota, crear una nueva
    #             if not updated:
    #                 self.env["account.payment.request"].create({
    #                     "company_id": acceptance.company_id.id,
    #                     "order_id": po.id,
    #                     "payment_term_id": po.payment_term_id.id if po.payment_term_id else False,
    #                     "quota": quota,
    #                     "date_maturity": acceptance.date_receive,
    #                     "partner_id": acceptance.partner_id.id,
    #                     "amount": amount,
    #                     "amount_original": amount,
    #                     "state": "draft",
    #                     "type": "purchase.order",
    #                     "manual_type": "purchase.order",
    #                     "description_motive": _("CUOTA %s DE %s") % (quota, po.name),
    #                     "request_type_id": self.env.ref("gps_bancos.req_type_anticipo_oc").id,
    #                     "percentage": percentage,
    #                     "document_ref": acceptance.name,
    #                     "date": acceptance.date_receive,
    #                     "is_prepayment": False,
    #                     'type_document':'work_acceptance',
    #                     'work_acceptance_id':acceptance.id
    #                 })
    #                 total += amount
    #                 quota += 1
    #
    #             # cuotas restantes no manejadas → eliminarlas
    #             (requests - handled_requests).unlink()
    #
    #             # cuota final si queda saldo
    #             remaining = round(po.amount_total - total, 2)
    #             if remaining > 0:
    #                 self.env["account.payment.request"].create({
    #                     "company_id": acceptance.company_id.id,
    #                     "order_id": po.id,
    #                     "payment_term_id": po.payment_term_id.id if po.payment_term_id else False,
    #                     "quota": quota,
    #                     "date_maturity": po.date_order or TODAY,
    #                     "partner_id": po.partner_id.id,
    #                     "amount": remaining,
    #                     "amount_original": remaining,
    #                     "state": "draft",
    #                     "type": "purchase.order",
    #                     "manual_type": "purchase.order",
    #                     "description_motive": _("CUOTA %s (FINAL) DE %s") % (quota, po.name),
    #                     "request_type_id": self.env.ref("gps_bancos.req_type_anticipo_oc").id,
    #                     "percentage": (po.amount_total > 0) and (remaining / po.amount_total) * 100 or 0.0,
    #                     "document_ref": acceptance.name,
    #                     "date": TODAY,
    #                     "is_prepayment": False,
    #                     'type_document':'work_acceptance',
    #                     'work_acceptance_id':acceptance.id
    #                 })
    #     return res