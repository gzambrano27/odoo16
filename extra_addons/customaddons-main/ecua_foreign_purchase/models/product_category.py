from odoo import fields, models, api

ACCOUNT_DOMAIN = "['&', '&', '&', ('deprecated', '=', False), ('account_type','=','asset_current'), ('company_id', '=', " \
                 "current_company_id), ('is_off_balance', '=', False)]"


class ProductCategory(models.Model):
    _inherit = 'product.category'

    purchase_tariff_id = fields.Many2one('purchase.tariff', 'Arancel')

    def default_account_importation(self):
        account = self.env['ir.config_parameter'].sudo().get_param(
            'ecua_foreign_purchase.account_importation_id')
        if account:
            account_id = self.env["account.account"].browse(int(account))
            return account_id if account_id else False

    property_account_importation_id = fields.Many2one('account.account', company_dependent=True,
                                                      string="Importation Account",
                                                      domain=ACCOUNT_DOMAIN,
                                                      default=default_account_importation,
                                                      help="This account will be used when validating a customer invoice.")
