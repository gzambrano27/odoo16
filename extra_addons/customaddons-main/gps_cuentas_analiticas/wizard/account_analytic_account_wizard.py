# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from json import dumps

from odoo import _, api, fields, models,SUPERUSER_ID
from odoo.exceptions import ValidationError
from datetime import date, timedelta

REPORTS={
    "all":"gps_cuentas_analiticas.account_analytic_account_xlsx_act",
    "account_move":"gps_cuentas_analiticas.account_anlyt_acct_move_xlsx_act"
}
class AccountAnalyticAccountWizard(models.TransientModel):
    _name = "account.analytic.account.wizard"
    _description="Asistente para Cuentas Analiticas"

    company_ids = fields.Many2many(
        'res.company',
        'res_company_analyic_account_wizard_rel',
        'wizard_id',
        'company',
        'Compañías'
    )

    analytic_ids = fields.Many2many(
        'account.analytic.account',
        'account_analytic_account_analytic_wizard_rel',
        'wizard_id',
        'account_id',
        'Cuentas Analíticas'

    )

    date_from = fields.Date(
        string="Fecha Inicial",
        default=lambda self: date.today() - timedelta(days=365)
    )
    date_to = fields.Date(
        string="Fecha Final",
        default=fields.Date.context_today
    )

    type=fields.Selection([('all','Todas las cuentas'),
                           ('account_move','Linea de Asientos')],srtring="Tipo",default="all")

    @api.onchange('company_ids')
    def _onchange_company_ids(self):
        """ Actualiza el dominio de analytic_ids basado en las compañías seleccionadas. """
        self.analytic_ids=[(6,0,[])]
        if self.company_ids:
            return {'domain': {'analytic_ids': [('company_id', 'in', self.company_ids.ids)]}}
        return {'domain': {'analytic_ids': []}}

    def process(self):
        self = self.with_context({"no_raise": True})
        self = self.with_user(SUPERUSER_ID)
        #REPORT = "gps_cuentas_analiticas.account_analytic_account_xlsx_act"
        for brw_each in self:
            REPORT=REPORTS[brw_each.type]
            try:
                OBJ_REPORTS = self.env[self._name].sudo()
                context = dict(active_ids=[brw_each.id],
                               active_id=brw_each.id,
                               active_model=self._name,
                               landscape=True
                               )
                OBJ_REPORTS = OBJ_REPORTS.with_context(context)
                report_value = OBJ_REPORTS.env.ref(REPORT).with_user(SUPERUSER_ID).report_action(OBJ_REPORTS)
                report_value["target"] = "new"
                return report_value
            except Exception as e:
                raise ValidationError(_("Error al Imprimir %s -- %s") % (REPORT, str(e),))