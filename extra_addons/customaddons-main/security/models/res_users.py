# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)

class ResUsers(models.Model):    
    _inherit="res.users"  
    
    def resolve_user_group_ref(self,module_name,group_ref):
        for brw_each in self:     
            result_group = self.env["ir.model.data"].get_object_reference(module_name, group_ref)
            if not result_group:
                return False
            self._cr.execute("""SELECT COUNT(1) FROM RES_GROUPS_USERS_REL WHERE GID=%s AND UID=%s""",(result_group[1],brw_each.id))
            result=self._cr.fetchone()
            if not result:
                return False
            return (result[0]>0)
        return False
    
    @api.model
    def get_users_group_ref(self,module_name,group_ref):
        result_group = self.env["ir.model.data"].get_object_reference(module_name, group_ref)
        if not result_group:
            return []
        self._cr.execute("""SELECT UID,UID FROM RES_GROUPS_USERS_REL WHERE GID=%s""",(result_group[1],))
        result=self._cr.fetchall()
        if not result:
            return []
        return list(dict(result).keys())
    
