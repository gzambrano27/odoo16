# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models

class IrActionsServer(models.Model):    
    _inherit="ir.actions.server"
    
    @api.model
    def _get_eval_context(self, action=None):
        eval_context=super(IrActionsServer,self)._get_eval_context(action)
        localdict,global_dict=self.env["dynamic.function"].sudo().initialize()
        eval_context.update(localdict)
        return eval_context
    
