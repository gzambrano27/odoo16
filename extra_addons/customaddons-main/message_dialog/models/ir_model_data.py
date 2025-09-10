# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models,_
import logging
_logger = logging.getLogger(__name__)

class IrModelData(models.Model):    
    _inherit="ir.model.data"
    
    @api.model
    def invoke_action(self,res_model,description,
                      domain,
                      module_tree_view,module_form_view,module_search_view,
                      module_tree_view_ref,module_form_view_ref,module_search_view_ref,
                      context=None):
        tree_id = self.resolve_view_ref(module_tree_view,module_tree_view_ref)
        form_id = self.resolve_view_ref(module_form_view,module_form_view_ref)
        search_id = self.resolve_view_ref(module_search_view,module_search_view_ref)
        return {
                        'domain': domain,
                        'name': description,
                        'view_mode': 'tree, form',
                        'search_view_id': search_id ,
                        'res_model': res_model,
                        'views': [(tree_id, 'tree'), (form_id, 'form')],
                        "context":context,
                        'type': 'ir.actions.act_window'
                    }  
    
    @api.model
    def resolve_view_ref(self,module_name,module_view):
        view_res = self._xmlid_lookup("%s.%s" % (module_name, module_view))
        view_id = view_res and view_res[2] or False
        return view_id
    
    @api.model       
    def invoke_wizard(self,res_model,res_id,context=None,description=None):
        if context is None:
            context={}
        return {
                'type': 'ir.actions.act_window',
                'res_model': res_model,
                'name': (description is None and '' or description),
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': res_id,
                'views': [(False, 'form')],
                'target': 'new',
                "context":context                
            }
        
