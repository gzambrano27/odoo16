from odoo import models, fields, api

class ProductCategory(models.Model):
    _inherit = 'product.category'

    import_account_transit_debit = fields.Many2one(
        'account.account', string="Cuenta Transitoria Débito (Importación)")
    import_account_transit_credit = fields.Many2one(
        'account.account', string="Cuenta Transitoria Crédito (Importación)")