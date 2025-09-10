# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class HrPayrollStructure(models.Model):
    _inherit = "hr.payroll.structure"

    journal_id = fields.Many2one("account.journal", "Diario", required=False)
    default = fields.Boolean("Por Defecto", default=False)
    active = fields.Boolean("Activo", default=True)

    account = fields.Boolean(string="Realizar Contabilidad", default=False,store=False, readonly=True, related="type_id.account")
    legal_iess = fields.Boolean(string="Para Afiliados",default=False,store=False, readonly=True, related="type_id.legal_iess")

    struct_rule_ids = fields.Many2many("hr.salary.rule", "hr_payroll_struct_rules_rel", "struct_id", "rule_id",
                                       "Reglas", domain=[])

    _sql_constraints = [("hr_payroll_struct_unique_code", "unique(code)", _("Código debe ser único")),
                        ("hr_payroll_struct_unique_name", "unique(name)", _("Nombre debe ser único"))]

    _order = "default desc,active desc"

    @api.depends('struct_rule_ids')
    def _get_compute_struct_rule_ids(self):
        for brw_each in self:
            brw_each.rule_ids = brw_each.struct_rule_ids

    @api.onchange('type_id')
    def onchange_type_id(self):
        legal_iess = False
        if self.type_id:
            legal_iess = self.type_id.legal_iess
        self.legal_iess = legal_iess

    @api.model
    def _where_calc(self, domain, active_test=True):
        # if not domain:
        #     domain=[]
        # filter_contract_type_id=self._context.get("filter_contract_type_id",False)
        # if filter_contract_type_id:
        #     self._cr.execute("""SELECT STRUCTURE_ID,STRUCTURE_ID FROM CONTRACT_TYPE_STRUCT_REL WHERE CONTRACT_TYPE_ID=%s """ , (self._context["filter_contract_type_id"],))
        #     result=self._cr.fetchall()
        #     if result:
        #         structure_ids=dict(result).keys()
        #         domain.append(("id","in",tuple(structure_ids) ))
        #     else:
        #         domain.append(("id","=",-1))
        return super(HrPayrollStructure, self)._where_calc(domain, active_test)
