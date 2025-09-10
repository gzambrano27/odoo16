from odoo import exceptions, _
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class AccountInvoice(models.Model):
    _inherit = 'account.move'

    def visualizar_relacionar_importacion(self):
        return {
            'name': "Relacionar Importación",
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref(
                'ecua_foreign_purchase.view_purchase_asign_invoice_ft_form').id,
            'res_model': 'purchase.asign.invoice',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    importation_id = fields.Many2one('trade.importation', 'Orden de Importación')
    es_importacion = fields.Boolean('Es Importacion?')

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.constrains('importacion', 'invoice_method')
    def _check_invoice_method(self):
        """
        Obliga a seleccionar 'On ordered quantities' si es importación.
        """
        for record in self:
            if record.importacion and record.invoice_method != 'purchase':
                raise ValidationError(
                    "Cuando el pedido es de importación, el Método de Facturación debe ser 'Cantidades Ordenadas'."
                )
            
    def _prepare_invoice(self):
        """Prepare the dict of values to create the new invoice for a purchase order.
        """
        self.ensure_one()
        move_type = self._context.get('default_move_type', 'in_invoice')

        partner_invoice = self.env['res.partner'].browse(self.partner_id.address_get(['invoice'])['invoice'])
        partner_bank_id = self.partner_id.commercial_partner_id.bank_ids.filtered_domain(['|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)])[:1]

        invoice_vals = {
            'ref': self.partner_ref or '',
            'move_type': move_type,
            'narration': self.notes,
            'currency_id': self.currency_id.id,
            'invoice_user_id': self.user_id and self.user_id.id or self.env.user.id,
            'partner_id': partner_invoice.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id._get_fiscal_position(partner_invoice)).id,
            'payment_reference': self.partner_ref or '',
            'partner_bank_id': partner_bank_id.id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
            'es_importacion': self.importacion,
        }
        return invoice_vals
    
        
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    def _prepare_account_move_line(self, move=False):
        self.ensure_one()
        aml_currency = move and move.currency_id or self.currency_id
        date = move and move.date or fields.Date.today()
        if self.order_id.importacion:
            if not self.product_id.categ_id.import_account_transit_debit:
                raise UserError(_('No se ha configurado en la categoria del producto la cuenta transitoria de importacion!!'))
            res = {
                'display_type': self.display_type or 'product',
                'name': '%s: %s' % (self.order_id.name, self.name),
                'product_id': self.product_id.id,
                'product_uom_id': self.product_uom.id,
                'account_id':self.product_id.categ_id.import_account_transit_debit.id,
                'quantity': self.qty_to_invoice,
                'price_unit': self.currency_id._convert(self.price_unit, aml_currency, self.company_id, date, round=False),
                'tax_ids': [(6, 0, self.taxes_id.ids)],
                'purchase_line_id': self.id,
            }
        else:
            res = {
                'display_type': self.display_type or 'product',
                'name': '%s: %s' % (self.order_id.name, self.name),
                'product_id': self.product_id.id,
                'product_uom_id': self.product_uom.id,
                'quantity': self.qty_to_invoice,
                'price_unit': self.currency_id._convert(self.price_unit, aml_currency, self.company_id, date, round=False),
                'tax_ids': [(6, 0, self.taxes_id.ids)],
                'purchase_line_id': self.id,
            }
        if self.analytic_distribution and not self.display_type:
            res['analytic_distribution'] = self.analytic_distribution
        return res
    