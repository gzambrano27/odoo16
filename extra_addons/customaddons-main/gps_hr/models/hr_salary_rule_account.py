# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class HrSalaryRuleAccount(models.Model):
    _name = "hr.salary.rule.account"
    _description = "Cuentas de Rubros para asientos"

    @api.model
    def _get_default_company_id(self):
        if self._context.get("allowed_company_ids", []):
            return self._context.get("allowed_company_ids", [])[0]
        return False

    type = fields.Selection([('process', 'Proceso'),
                             ('payslip', 'Rol')], string="Tipo", required=True, default="process")
    rule_id = fields.Many2one("hr.salary.rule", string="Rubro", ondelete="cascade")
    account_type = fields.Selection([("debit", "Debe"), ("credit", "Haber")], string="Nat. Cta.", required=True,
                                    default="debit")
    company_id = fields.Many2one("res.company", "Empresa", required=True, default=_get_default_company_id)
    account_id = fields.Many2one("account.account", "Cuenta",required=True)
    journal_id=fields.Many2one("account.journal","Diario",required=False)

    required_journal=fields.Boolean(string="Requiere Diario",compute="_get_compute_required_journal",store=False,readonly=True)

    analytic_ids = fields.One2many("hr.salary.rule.account.analytic","rule_account_id", "Cuentas Analiticas")

    @api.onchange('type','account_type','rule_id')
    @api.depends('type', 'account_type', 'rule_id')
    def _get_compute_required_journal(self):
        for brw_each in self:
            required_journal=False
            if brw_each.type=='process':
                if brw_each.rule_id.category_id.code=="OUT":
                    required_journal= brw_each.account_type=="debit"
                else:
                    required_journal = brw_each.account_type == "credit"
            brw_each.required_journal=required_journal