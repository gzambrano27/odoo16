# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID


class DocumentFinancialLinePaymentGroup(models.Model):
    _name = "document.financial.line.payment.group"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Pago Agrupado de Operacion Financiera"

    document_id = fields.Many2one(
        "document.financial",
        string="Operacion Financiera", ondelete="cascade"
    )
    document_cobro_id= fields.Many2one(
        "document.financial",
        string="Operacion Financiera para Recaudacion", ondelete="cascade"
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related="company_id.currency_id",store=False,readonly=True)
    date_process = fields.Date("Fecha de Pago", required=True)
    amount = fields.Monetary("Aplicado",  default=0.00,store=True,readonly=True,compute="_compute_amount")

    payment_capital = fields.Monetary("Capital", default=0.00, store=True,readonly=True,compute="_compute_amount")
    payment_interest = fields.Monetary("Interés", default=0.00, store=True,readonly=True,compute="_compute_amount")
    payment_overdue_interest = fields.Monetary("Interés Mora", default=0.00, store=True,readonly=True,compute="_compute_amount")
    payment_other = fields.Monetary("Otros", default=0.00, required=False,store=True,readonly=True,compute="_compute_amount")

    payment_amount = fields.Monetary("Monto", default=0.00, store=True, readonly=True, compute="_compute_amount")
    payment_amount_interest = fields.Monetary("Interés", default=0.00, store=True, readonly=True, compute="_compute_amount")


    name = fields.Char("# Documento", default=None, size=32, required=True)
    migrated=fields.Boolean("Migrado",default=False)
    is_cancel = fields.Boolean("Anulado", default=False)
    ref=fields.Char("# Referencia",default=None,size=32,required=True)
    payment_id=fields.Many2one('account.payment','Pago')
    move_id = fields.Many2one('account.move', 'Asiento Pago/NC')
    payment_line_ids=fields.One2many('document.financial.line.payment','payment_group_id',"Detalle")

    state = fields.Selection([('validated', 'Válido'),
                              ('no_validated', 'No válido'),
                              ],string="Estado",default="draft",compute="_compute_state")

    internal_type = fields.Selection([
        ('out', 'Pagos'),
        ('in', 'Cobros'),

    ], string="Tipo de Operacion Interna", default="out", tracking=True)

    attachment_ids = fields.Many2many("ir.attachment", "document_financial_pay_group_attch_rel", "document_id",
                                      "attachment_id",
                                      "Adjuntos")

    _order="date_process asc,id asc"

    _rec_name="name"

    @api.depends('migrated','is_cancel','payment_id','payment_id.state','payment_id.reversed_payment_id')
    def _compute_state(self):
        for brw_each in self:
            state="validated"
            if brw_each.migrated:
                if brw_each.is_cancel:
                    state="no_validated"
            else:
                if not brw_each.payment_id:
                    state = "no_validated"
                else:
                    if brw_each.payment_id.state!="posted" or brw_each.payment_id.reversed_payment_id:
                        state = "no_validated"
            brw_each.state=state

    @api.depends('payment_line_ids.amount','payment_line_ids')
    def _compute_amount(self):
        DEC=2
        for brw_each in self:
            payment_amount,payment_amount_interest,amount,payment_capital,payment_interest,payment_overdue_interest,payment_other=0.00,0.00,0.00,0.00,0.00,0.00,0.00
            for brw_lines in brw_each.payment_line_ids:
                payment_capital += round(brw_lines.payment_capital, DEC)
                payment_interest += round(brw_lines.payment_interest, DEC)
                payment_overdue_interest += round(brw_lines.payment_overdue_interest, DEC)
                payment_other += round(brw_lines.payment_other, DEC)
                #####################################################################################################################
                payment_amount += round(brw_lines.payment_amount, DEC)
                payment_amount_interest += round(brw_lines.payment_interes_generado, DEC)
                #####################################################################################################################
                amount += round(brw_lines.amount, DEC)

            brw_each.amount=amount
            brw_each.payment_capital = payment_capital
            brw_each.payment_interest = payment_interest
            brw_each.payment_overdue_interest = payment_overdue_interest
            brw_each.payment_other = payment_other

            brw_each.payment_amount = payment_amount
            brw_each.payment_amount_interest = payment_amount_interest



    def action_cancel(self):
        self.ensure_one()
        brw_each=self
        if brw_each.is_cancel:
            raise ValidationError(_("Documento ya fue cancelado o reversado!!!"))
        if brw_each.migrated:
            brw_each.write({"is_cancel":True})
        else:
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'Reversar Pago',
                    'res_model': 'account.payment.cancel.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_payment_id': self.payment_id.id,  # Puedes pasar valores al wizard si quieres
                        'default_active_id':self.payment_id.id,
                        'default_active_ids': [self.payment_id.id],
                        'default_active_model':'account.payment',
                        'default_full_reversed':True,
                        ####
                        'active_id': self.payment_id.id,
                        'active_ids': [self.payment_id.id],
                        'active_model': 'account.payment',
                    }
            }



