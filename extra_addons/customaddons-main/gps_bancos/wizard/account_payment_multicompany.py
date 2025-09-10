from odoo import models, fields, api
from zeep.exceptions import ValidationError


class AccountPaymentMultiCompany(models.TransientModel):
    _name = 'account.payment.multicompany'
    _description = 'Asistente de Pago por Compañía'

    @api.model
    def _get_active_macros(self):
        active_ids = self._context.get('active_ids', [])
        print(active_ids)
        macros = self.env['account.payment.bank.macro.summary'].browse(active_ids)
        return macros

    @api.model
    def _get_default_company(self):
        macros = self._get_active_macros()
        if not macros:
            return False
        partner = macros[0].partner_id
        company = self.env['res.company'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if not company:
            raise ValidationError(f"No se encontró una compañía vinculada al partner: {partner.name}")

        return company


    @api.model
    def _get_default_partner(self):
        #print(self.context)
        macros = self._get_active_macros()
        if not macros:
            return False
        partner = macros[0].partner_id
        return partner.id

    @api.model
    def _get_default_amount(self):
        macros = self._get_active_macros()
        return sum(mac.amount for mac in macros)

    @api.model
    def _get_allowed_companies(self):
        allow_company = self._get_default_company()
        return allow_company and [allow_company.id] or []

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        store=True,
        readonly=True,
        required=False,
        default=_get_default_company
    )

    partner_id= fields.Many2one('res.partner', string='Compañía', store=True, readonly=True, required=False,
                      default=_get_default_partner)
    account_id = fields.Many2one(
        'account.account',
        string='Cuenta Contable',
        required=True,
        domain=[],
        context=lambda self: {
            'allowed_company_ids': self ['res.company'].sudo().search([]).ids
        },
        check_company=False
    )
    amount = fields.Monetary(string='Monto',store=True,readonly=True,  required=True,default=_get_default_amount)
    currency_id = fields.Many2one('res.currency', compute='_compute_currency_id', store=False, readonly=True)
    analytic_id=fields.Many2one('account.analytic.account',"C. Analitica")

    @api.depends('partner_id')
    def _compute_currency_id(self):
        for rec in self:
            rec.currency_id = rec._get_default_company().currency_id

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """
        Filtrar cuentas contables por:
        - Compañías en allowed_company_ids
        - Compañía asociada al partner
        """
        allowed_companies = []#self.env.companies.ids
        partner_company = self.env['res.company'].sudo().search([
            ('partner_id', '=', self.partner_id.id)
        ], limit=1)
        partner_company_id = partner_company.id if partner_company else False

        # Construir dominio
        domain = [('company_id', '=', partner_company_id)]

        return {'domain': {'account_id': domain}}

    def action_confirm(self):
        self=self.sudo()
        allowed_company_ids=self._context.get('allowed_company_ids',[])
        for brw_each in self:
            allowed_company_ids+=[brw_each.company_id.id]
            brw_each=brw_each.with_context(allowed_company_ids=allowed_company_ids)
            macros=brw_each._get_active_macros()
            macros._create_payment_multicompany(brw_each.account_id,brw_each.analytic_id)

        return True