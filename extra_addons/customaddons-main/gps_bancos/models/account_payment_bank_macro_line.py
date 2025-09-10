# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime

class AccountPaymentBankMacroLine(models.Model):
    _name = 'account.payment.bank.macro.line'
    _description = "Detalle de Pagos con Macros Bancarias"

    bank_macro_id=fields.Many2one("account.payment.bank.macro","Macro",ondelete="cascade")
    request_id=fields.Many2one("account.payment.request","Solicitud",ondelete="cascade")
    type = fields.Selection(related="request_id.type", store=False, readonly=True)
    partner_id = fields.Many2one(related="request_id.partner_id", store=False, readonly=True)
    company_id = fields.Many2one(related="request_id.company_id", store=False, readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)

    document_ref = fields.Html(related="request_id.document_ref", store=False, readonly=True)

    original_pending=fields.Monetary("Pendiente Original",required=True)
    original_amount = fields.Monetary("Por Pagar Original", required=True)
    pending=fields.Monetary("Pendiente",required=True)
    amount = fields.Monetary("Por Pagar", required=True)

    bank_account_id = fields.Many2one("res.partner.bank", "Cuenta de Banco", required=False)
    apply=fields.Boolean("Aplicar",default=True)

    is_prepayment = fields.Boolean("Es Anticipo", default=False)
    prepayment_account_id = fields.Many2one("account.account", "Cuenta Contable", required=False,domain=[('deprecated','=',False),('prepayment_account','=',True)])

    payment_id=fields.Many2one("account.payment","Pago")
    ref=fields.Char("# Referencia")
    comments = fields.Text("Glosa")
    reversed = fields.Boolean('Fue reversado')

    payment_account_id = fields.Many2one("account.account", "Cuenta Contable Pago Proveedor",compute="_compute_payment_account_id",store=True,readonly=True)

    default_mode_payment = fields.Selection(related="bank_macro_id.default_mode_payment",store=False,readonly=True)

    @api.depends('request_id.partner_id','request_id.invoice_line_id','request_id.invoice_id')
    def _compute_payment_account_id(self):
        for record in self:
            payment_account_id = record.request_id.partner_id.property_account_payable_id and record.request_id.partner_id.property_account_payable_id.id or False
            if record.request_id.type in ('purchase.order','request'):
                if record.request_id.enable_other_account:
                    payment_account_id=record.request_id.other_account_id.id
                else:
                    if record.is_prepayment:
                        payment_account_id=record.prepayment_account_id and record.prepayment_account_id.id or False
            if record.request_id.type=='account.move':
                if record.request_id.invoice_line_id:
                    payment_account_id=record.request_id.invoice_line_id.account_id and record.request_id.invoice_line_id.account_id.id or False
                else:
                    if record.request_id.invoice_id:
                        payable_line = record.request_id.invoice_id.line_ids.filtered(
                            lambda line: line.partner_id==record.request_id.partner_id and  line.account_id.account_type == 'liability_payable'
                        )
                        if payable_line:
                            payment_account_id = payable_line[0].account_id.id
            if record.request_id.type == 'hr.employee.payment':
                if record.request_id.payment_employee_id:
                    payment_account_id = record.request_id.payment_employee_id.move_ids.filtered(lambda x: x.debit>0).mapped('account_id')#x.partner_id== record.request_id.partner_id

            if record.request_id.type == 'hr.employee.liquidation':
                if record.request_id.liquidation_employee_id:
                    payment_account_id = record.request_id.company_id.get_payment_conf().liquidation_account_id

            record.payment_account_id=payment_account_id

    @api.constrains('amount', 'pending','apply')
    def _check_amount_limits(self):
        for record in self:
            if record.apply:
                if record.amount <= 0:
                    raise ValidationError("El monto pagado debe ser mayor a 0.Ver Sol. %s , %s" % (record.request_id.id,record.request_id.name))
                if record.amount > record.pending:
                    raise ValidationError("El monto pagado no puede ser mayor al valor pendiente.Ver Sol. %s , %s" % (record.request_id.id,record.request_id.name))

    @api.onchange('apply')
    def onchange_apply(self):
        if not self.apply:
            self.amount=0.00
        else:
            self.amount=self.pending

    @api.onchange('amount','apply')
    def _onchange_amount(self):
        if self.apply:
            if self.amount <= 0:
                return {
                    'warning': {
                        'title': "Valor inválido",
                        'message': "El monto pagado debe ser mayor a 0.",
                    }
                }
            if self.amount > self.pending:
                return {
                    'warning': {
                        'title': "Valor inválido",
                        'message': "El monto pagado no puede ser mayor al valor pendiente.",
                    }
                }

    @api.depends('amount', 'pending')
    def _compute_amount_validation(self):
        for record in self:
            if record.apply:
                if not (0 < record.amount <= record.pending):
                    raise ValidationError("El monto pagado debe ser mayor a 0 y menor o igual al valor pendiente.")

    _rec_name="id"

    #@api.model
    # def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
    #     if domain is None:
    #         domain = []
    #     if "filter_type_struct_id" in self._context:
    #         # structs_by_type=self.env["hr.payroll.structure"].sudo().search([('type_id','=',self._context["filter_type_struct_id"])])
    #         # structs_ids=structs_by_type.ids+[-1,-1]
    #         filter_legal_iess = self._context.get("filter_legal_iess", False)
    #
    #         srch_contract = self.env["hr.contract"].sudo().search([('state', 'in', ('open',)),
    #                                                                ('company_id', '=', self.env.company.id),
    #                                                                # ('contract_type_id','in',structs_ids),
    #                                                                ('contract_type_id.legal_iess', '=',
    #                                                                 filter_legal_iess),
    #                                                                ])
    #         employees = srch_contract.mapped('employee_id').ids
    #         employees += [-1]
    #         domain += [('id', 'in', employees)]
    #     result = super(HrEmployee, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit,
    #                                                  order=order)
    #     return result
    #