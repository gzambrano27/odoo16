from odoo import models, fields

class PurchaseRequestLineExportWizard(models.TransientModel):
    _name = 'purchase.request.line.export.wizard'
    _description = 'Export Requisiciones Wizard'

    file_data = fields.Binary("Archivo", readonly=True)
    file_name = fields.Char("Nombre de archivo", readonly=True)