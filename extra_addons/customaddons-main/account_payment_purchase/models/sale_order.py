from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    referencia_analitica = fields.Char(string='Referencia Analítica')


    def _prepare_analytic_account_data(self, prefix=None):
        """ Prepare SO analytic account creation values.

        :param str prefix: The prefix of the to-be-created analytic account name
        :return: `account.analytic.account` creation values
        :rtype: dict
        """
        self.ensure_one()
        name = self.name
        if prefix:
            name = prefix + ": " + self.name
        plan = self.env['account.analytic.plan'].sudo().search([
            '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)
        ], limit=1)
        if not plan:
            plan = self.env['account.analytic.plan'].sudo().create({
                'name': 'Default',
                'company_id': self.company_id.id,
            })
        return {
            'name': self.lead_project_id.code+':'+self.lead_project_id.name,#name,
            'code': self.lead_project_id.name,#self.client_order_ref,
            'company_id': self.company_id.id,
            'plan_id': plan.id,
            'partner_id': self.partner_id.id,
        }