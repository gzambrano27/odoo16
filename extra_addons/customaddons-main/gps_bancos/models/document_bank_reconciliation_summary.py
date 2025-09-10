from odoo import models, fields

class DocumentBankReconciliationSummary(models.Model):
    _name = 'document.bank.reconciliation.summary'
    _description = 'Resumen de Conciliación Bancaria'

    document_id = fields.Many2one('document.bank.reconciliation', string='Documento', ondelete="cascade")
    company_id = fields.Many2one('res.company', string='Compañía', required=True, index=True)
    type_id = fields.Many2one('document.bank.reconciliation.type', string='Tipo', required=False, index=True)
    total_amount = fields.Monetary(string='Monto Total', required=True)
    currency_id = fields.Many2one('res.currency', string="Moneda", required=True)

    _sql_constraints = [
        ('unique_summary_line', 'unique(document_id,company_id, type_id)',
         'Ya existe un resumen para esta combinación de Compañía y Tipo.')
    ]


