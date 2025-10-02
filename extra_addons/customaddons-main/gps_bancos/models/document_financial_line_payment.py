# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID


class DocumentFinancialLinePayment(models.Model):
    _name = "document.financial.line.payment"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Pago de Operacion Financiera"

    line_id = fields.Many2one(
        "document.financial.line",
        string="Detalle de Operacion Financiera", ondelete="cascade",tracking=True
    )
    document_id = fields.Many2one(
        related="line_id.document_id",store=True,readonly=True
    )
    company_id = fields.Many2one(
        related="line_id.company_id",store=True,readonly=True
    )
    currency_id = fields.Many2one(related="company_id.currency_id",store=True,readonly=True)
    date_process = fields.Date(related="payment_group_id.date_process",store=True,readonly=True)
    amount = fields.Monetary("Aplicado",  default=0.00,required=True,tracking=True)

    payment_capital = fields.Monetary("Capital", default=0.00, required=False,tracking=True)#
    payment_interest = fields.Monetary("Interés", default=0.00, required=False,tracking=True)#
    payment_overdue_interest = fields.Monetary("Interés Mora", default=0.00, required=False,tracking=True )#
    payment_other = fields.Monetary("Otros", default=0.00, required=False,tracking=True)#
    ####################################################################################################
    payment_amount = fields.Monetary("Valor", default=0.00, required=False, tracking=True)  #
    payment_interes_generado = fields.Monetary("Interés Generado", default=0.00, required=False, tracking=True)  #
    ####################################################################################################
    name = fields.Char(related="payment_group_id.name",store=True,readonly=False)

    migrated=fields.Boolean(related="payment_group_id.migrated",store=True,readonly=False)

    ref=fields.Char(related="payment_group_id.ref",store=True,readonly=False)

    payment_id=fields.Many2one(related="payment_group_id.payment_id",store=True,readonly=False)
    move_id = fields.Many2one(related="payment_group_id.move_id", store=True, readonly=False)

    payment_group_id=fields.Many2one('document.financial.line.payment.group',"Pago Agrupado",ondelete="cascade")

    state = fields.Selection(related="payment_group_id.state", store=True, readonly=False)

    _order="payment_group_id asc,line_id asc,amount asc"

    _rec_name="name"

