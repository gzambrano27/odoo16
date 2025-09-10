from odoo import models, fields, api,_
from odoo.exceptions import ValidationError
import re

class UpdateReconciliationTypeWizard(models.TransientModel):
    _name = 'update.reconciliation.type.wizard'
    _description = 'Actualizar Tipo de Movimiento Bancario'

    @api.model
    def _get_default_document_financial_id(self):
        brw_lines = self.env["document.bank.reconciliation.line"].sudo().browse(self._context.get("active_ids"))
        return brw_lines.document_id.id

    @api.model
    def _get_default_document_journal_id(self):
        brw_lines = self.env["document.bank.reconciliation.line"].sudo().browse(self._context.get("active_ids"))
        return brw_lines.document_id.journal_id.id

    @api.model
    def _get_default_document_ref(self):
        brw_lines = self.env["document.bank.reconciliation.line"].sudo().browse(self._context.get("active_ids", []))
        all_refs = brw_lines.mapped('reference')
        unique_refs = [ref for ref in all_refs if all_refs.count(ref) == 1]
        return ','.join(unique_refs)

    @api.model
    def _get_default_payment_total(self):
        DEC=2
        brw_lines = self.env["document.bank.reconciliation.line"].sudo().browse(self._context.get("active_ids"))
        payment_total = sum(brw_lines.mapped('signed_amount'))
        return round(abs(payment_total),DEC)

    @api.model
    def _get_default_signed_payment_total(self):
        DEC = 2
        brw_lines = self.env["document.bank.reconciliation.line"].sudo().browse(self._context.get("active_ids"))
        payment_total = sum(brw_lines.mapped('signed_amount'))
        return round(payment_total, DEC)

    type_id = fields.Many2one(
        'document.bank.reconciliation.type',
        string="Tipo de Documento",
        required=False
    )
    document_financial_id = fields.Many2one("document.bank.reconciliation", "Documento", ondelete="cascade",
                                            default=_get_default_document_financial_id)

    company_id = fields.Many2one(related="document_financial_id.company_id", store=False, readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)
    message = fields.Text("Comentarios")
    ref = fields.Text("Referencia",   default=_get_default_document_ref)
    date=fields.Date("Fecha",default=fields.Date.context_today)
    payment_total = fields.Monetary("Total",  required=False,readonly=True, store=True,   default=_get_default_payment_total)
    signed_payment_total = fields.Monetary("Total con Signo",   required=False,readonly=True, store=True,   default=_get_default_signed_payment_total)
    journal_id = fields.Many2one('account.journal', 'Diario', required=False,default=_get_default_document_journal_id)
    #recon_line_ids = fields.Many2many('document.bank.reconciliation.line','pay_recons_wzrd_bank_line_rel','wizard_id', 'line_id', "Detalle de Cuentas",   default=_get_default_active_ids)
    partner_id=fields.Many2one('res.partner','Proveedor')
    account_id=fields.Many2one('account.account','Cuenta Contable')
    analytic_id = fields.Many2one("account.analytic.account", "Cuenta Analitica")

    def action_apply_type(self):
        if not self._context.get('active_ids',[]):
            raise ValidationError("Debe seleccionar al menos una línea.")
        recon_line_ids=self.env['document.bank.reconciliation.line'].browse(self._context.get('active_ids',[]))
        recon_line_ids.write({'type_id': self.type_id.id})
        return {'type': 'ir.actions.act_window_close'}

    def limpiar_nombre_banco(self,texto):
        # Eliminar la palabra "banco" sin importar mayúsculas
        texto = re.sub(r'\bbanco\b', '', texto, flags=re.IGNORECASE)
        # Eliminar todos los números
        texto = re.sub(r'\d+', '', texto)
        # Eliminar espacios duplicados y recortar
        return texto.strip()

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        if self.journal_id:
            name=self.limpiar_nombre_banco(self.journal_id.name)
            srch=self.env["res.partner"].sudo().search([('name','ilike',name)])
            if len(srch)==1:
                self.partner_id=srch[0].id

    @api.onchange('partner_id','signed_payment_total')
    def onchange_partner_id(self):
        if self.partner_id:
            if self.signed_payment_total<0.00:
                self.account_id=self.partner_id.property_account_payable_id and self.partner_id.property_account_payable_id.id or False

    def action_payment(self):
        DEC = 2
        payment_obj = self.env["account.payment"]
        OBJ_PERIOD_LINE = self.env["account.fiscal.year.line"].sudo()
        for brw_each in self:
            if brw_each.payment_total<=0.00:
                raise ValidationError(_("El valor seleccionado debe ser mayor a 0.00"))
            payment_date = brw_each.date
            brw_period, brw_period_line = OBJ_PERIOD_LINE.get_periods(payment_date, brw_each.company_id,
                                                                      for_account_payment=True)
            ref = brw_each.ref
            account_payment_method_manual_out = self.env.ref('account.account_payment_method_manual_out')
            outbound_payment_account_line = brw_each.journal_id.outbound_payment_method_line_ids.filtered(
                lambda line: line.payment_method_id == account_payment_method_manual_out
            )
            bank_account_id = outbound_payment_account_line.payment_account_id and outbound_payment_account_line.payment_account_id.id or brw_each.journal_id.default_account_id.id
            payment_res = {
                'payment_type': brw_each.signed_payment_total<0 and  "outbound" or 'inbound',
                'partner_id': brw_each.partner_id and brw_each.partner_id.id or False,
                'partner_type': brw_each.signed_payment_total<0 and  "supplier" or 'customer',
                'journal_id': brw_each.journal_id.id,
                'company_id': brw_each.company_id.id,
                'currency_id': brw_each.company_id.currency_id.id,
                'date': payment_date,
                'payment_method_id': account_payment_method_manual_out.id,
                'ref': ref,
                'bank_reference': ref,
                'is_prepayment': False,
                'period_id': brw_period.id,
                'period_line_id': brw_period_line.id,
                'payment_purchase_line_ids': [(5,)],
                "destination_account_id": bank_account_id,
                'change_payment': True
            }
            line_ids = [(5,)]
            amount = brw_each.payment_total
            for brw_line_reconciliation in self.env['document.bank.reconciliation.line'].browse(self._context.get('active_ids',[])):
                #if round(brw_line_reconciliation.accounted_amount,DEC)==0.00:
                #raise ValidationError(_("El valor por conciliar debe ser mayor a 0.00"))
                line_ids.append((0, 0, {
                    "account_id": brw_each.account_id.id,
                    "partner_id": brw_each.partner_id and brw_each.partner_id.id or False,
                    "name": brw_line_reconciliation.reference,
                    "credit":brw_line_reconciliation.transaction_type=='debit' and   brw_line_reconciliation.amount or 0.00,
                    "debit": brw_line_reconciliation.transaction_type=='credit' and   brw_line_reconciliation.amount or 0.00,
                    "analytic_id": brw_each.analytic_id and brw_each.analytic_id.id or False,
                    'reconciliation_line_id':brw_line_reconciliation.id,
                }))
            payment_res["amount"] = amount
            payment_res["payment_line_ids"] = line_ids
            payment = payment_obj.create(payment_res)
            payment.action_post()

        return True