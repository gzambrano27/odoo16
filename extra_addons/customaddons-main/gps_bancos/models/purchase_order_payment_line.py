# models/purchase_payment_line.py

from odoo import models, fields,api

class PurchaseOrderPaymentLine(models.Model):
    _name = 'purchase.order.payment.line'
    _description = 'Payment Applied to Purchase Order'

    order_id = fields.Many2one('purchase.order', string='Orden de Compra', ondelete='cascade')
    payment_id = fields.Many2one('account.payment', string='Pago',ondelete='cascade')
    amount = fields.Monetary(string='Monto Aplicado', required=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='order_id.currency_id', store=True)
    reconciled=fields.Boolean("Reconciliado Automatica",default=False)
    reconciled_date=fields.Datetime("Fecha de Pago",compute="compute_payments",store=True,readonly=True)
    reconciled_user_id=fields.Many2one("res.users","Usuario de Reconciliacion")

    @api.depends('payment_id','payment_id.date')
    def compute_payments(self):
        for brw_each in self:
            reconciled_date=brw_each.payment_id.date
            brw_each.reconciled_date=reconciled_date
