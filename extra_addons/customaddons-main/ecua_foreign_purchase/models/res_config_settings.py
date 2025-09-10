from odoo import fields, models, api

ACCOUNT_DOMAIN = "['&', '&', '&', ('deprecated', '=', False), ('account_type','=','asset_current'), ('company_id', '=', current_company_id), ('is_off_balance', '=', False)]"


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_importation_id = fields.Many2one('account.account', string="Importation Account")
    # is_company_details_empty = fields.Boolean(
    #     compute='_compute_is_company_details_empty',
    #     store=True,
    #     string="Is Company Details Empty"
    # )

    @api.depends('street', 'city', 'country_id')
    def _compute_is_company_details_empty(self):
        for company in self:
            company.is_company_details_empty = not any([
                company.street, company.city, company.country_id
            ])


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_importation_id = fields.Many2one('account.account',
                                             string="Importation Account",
                                             domain=ACCOUNT_DOMAIN,
                                             related='company_id.account_importation_id', readonly=False)

    @api.model
    def create(self, vals):
        self.env.company.write(
            {
                "account_importation_id": vals.get("account_importation_id",
                                                   False) or self.env.company.account_importation_id.id
            }
        )
        vals.pop("account_importation_id", None)
        return super().create(vals)


    