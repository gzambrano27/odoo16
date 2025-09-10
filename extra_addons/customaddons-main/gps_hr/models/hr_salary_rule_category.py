# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_

class HrSalaryRuleCategory(models.Model):    
    _inherit="hr.salary.rule.category"
    
    active=fields.Boolean("Activo",default=True)
    parent_id = fields.Many2one(ondelete="cascade")
    
    _sql_constraints = [("hr_salary_rule_category_unique_code","unique(code)",_("Código debe ser único"))] 
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args = []
        search_ids=[]
        if name:
            search_ids = self.search( [('code',operator,name)] + args, limit=limit)
        if not search_ids:
            search_ids = self.search( [('name',operator,name)] + args, limit=limit)
        result= (search_ids is not None) and search_ids.name_get() or []
        return result
    