    # License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError

class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    state=fields.Selection([('active','Activo'),
                            ('inactive','Inactivo')
                            ],string="Estado",default="active")
    
    companies_to_replicate_ids = fields.Many2many(
        'res.company', string="Replicar en compañías",
        domain=lambda self: [('id', '!=', self.env.company.id)],
        help="Selecciona las compañías donde replicar esta cuenta analítica."
    )
    
    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._replicate_to_companies()
        return record

    def write(self, vals):
        res = super().write(vals)
        self._replicate_to_companies()
        return res
    
    @api.constrains('plan_id')
    def _check_plan_company(self):
        for rec in self:
            if rec.plan_id and rec.plan_id.company_id != rec.company_id:
                raise UserError(_(
                    "El plan contable seleccionado no pertenece a la compañía de la cuenta analítica."
                ))

    def _replicate_to_companies(self):
        for company in self.companies_to_replicate_ids:
            # Verificar si ya existe
            existing = self.search([
                ('name', '=', self.name),
                ('code', '=', self.code),
                ('company_id', '=', company.id)
            ])
            if existing:
                continue

            # Buscar o clonar plan contable en la compañía destino
            new_plan = False
            if self.plan_id:
                new_plan = self.env['account.analytic.plan'].search([
                    ('name', '=', self.plan_id.name),
                    ('company_id', '=', company.id)
                ], limit=1)

                if not new_plan:
                    # 🔐 Evitar error de acceso usando sudo()
                    new_plan = self.plan_id.with_context(force_company=company.id).sudo().copy({
                        'company_id': company.id
                    })

            # Preparar los valores a replicar
            copy_vals = {
                'company_id': company.id,
                'plan_id': new_plan.id if new_plan else False,
                'root_plan_id': False,
                'companies_to_replicate_ids': [(5, 0, 0)],
            }

            self.with_context(force_company=company.id).copy(default=copy_vals)


    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        print(self._context)

        if not args:
            args = []

        # Verificar si el usuario pertenece al grupo gps_cuentas_analiticas.group_todas_ctas_analiticas
        user_has_group = self.env.user.has_group('gps_cuentas_analiticas.group_todas_ctas_analiticas')

        # Si el usuario pertenece al grupo, filtrar solo cuentas activas (ejemplo: state='active')
        if not user_has_group:
            args.append(('state', '=', 'active'))

        values = super(AccountAnalyticAccount, self).name_search(name=name, args=args, operator=operator, limit=limit)
        return values

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        print(self._context)

        if domain is None:
            domain = []

        # Verificar si el usuario pertenece al grupo gps_cuentas_analiticas.group_todas_ctas_analiticas
        user_has_group = self.env.user.has_group('gps_cuentas_analiticas.group_todas_ctas_analiticas')

        # Si el usuario pertenece al grupo, filtrar solo cuentas activas (ejemplo: state='active')
        if not user_has_group:
            domain.append(('state', '=', 'active'))

        return super(AccountAnalyticAccount, self).search_read(domain, fields=fields, offset=offset, limit=limit,
                                                               order=order)
    
