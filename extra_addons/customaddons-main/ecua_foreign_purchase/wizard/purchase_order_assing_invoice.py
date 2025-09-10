from odoo.addons import decimal_precision as dp
import math
import time
import logging
from odoo import exceptions, _
from odoo import api, fields, models, _


class PurchaseAsignInvoice(models.TransientModel):
    _name = 'purchase.asign.invoice'

    importation_id = fields.Many2one(
        'trade.importation',
        'Orden de Importación',
        required=True
    )
    advice = fields.Char('Warning')

    concept_id = fields.Many2one('purchase.concept.bill', 'Descripción')

    def action_asign(self):
        for obj in self:
            model_name = self._context.get('active_model')
            if model_name == 'account.move':
                inv_id = self._context.get('active_id')
                inv = self.env['account.move'].browse(inv_id)
                if inv.move_type not in ['in_receipt', 'in_invoice']:
                    raise exceptions.UserError('You cannot assign this document type.')

                if inv.move_type == 'in_invoice':
                    if inv.id in [i.invoice_id.id for i in obj.importation_id.invoices_ids]:  # noqa
                        raise exceptions.UserError('This invoice is already assigned.')

                    if obj.concept_id.id in [i.concept_id.id for i in obj.importation_id.invoices_ids]:  # noqa
                        raise exceptions.UserError('This type of document is already assigned in this import.')

                    self.env['purchase.invoice'].create({
                        'invoice_id': inv.id,
                        'importation_id': obj.importation_id.id,
                        'invoice_date': inv.invoice_date,
                        'invoice_number': inv.l10n_latam_document_number,
                        'concept_id': obj.concept_id.id
                    })

                if inv.move_type == 'in_receipt':
                    if inv.id in [i.voucher_id.id for i in obj.importation_id.voucher_ids]:  # noqa
                        raise exceptions.UserError('This receipt is already assigned.')

                    if obj.concept_id.id in [i.concept_id.id for i in obj.importation_id.voucher_ids]:  # noqa
                        raise exceptions.UserError('This type of document is already assigned in this import.')

                    self.env['purchase.voucher'].create({
                        'voucher_id': inv.id,
                        'importation_id': obj.importation_id.id,
                        'payment_date': inv.invoice_date,
                        'amount': inv.amount_total,
                        'concept_id': obj.concept_id.id
                    })

                inv.write({'importation_id': obj.importation_id.id})

        return {'type': 'ir.actions.act_window_close'}
