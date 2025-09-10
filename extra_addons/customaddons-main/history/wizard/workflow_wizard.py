# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models,_
from odoo.exceptions import UserError, AccessError, ValidationError, AccessDenied
import logging
_logger = logging.getLogger(__name__)

class WorkflowWizard(models.TransientModel):    
    _name="workflow.wizard"  
    _description="Workflow Wizard"
    
    state=fields.Selection([],string="Estado",required=True)
    comments=fields.Text("Comentario",required=False)
    
    @api.onchange('comments')
    def onchange_comments(self):
        for brw_each in self:
            brw_each.comments = brw_each.comments and brw_each.comments.upper() or ''
    
    def process(self):
        for brw_each in self:
            if not brw_each.state:
                raise ValidationError(_("Estado no definido"))
        return True
     
