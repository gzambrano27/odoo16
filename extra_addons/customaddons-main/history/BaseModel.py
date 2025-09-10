# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _
from odoo import api
from odoo.models import BaseModel as InheritBaseModel
from odoo.exceptions import ValidationError

def register_history_unlink(self):
    for brw_each in self:
        vals = brw_each.with_context(active_test=False).copy_data(None)[0]
        self.env["log.history"].register(self._name,brw_each.id,_("REGISTRO ELIMINADO"),"unlinked",vals,brw_each[self._rec_name])
    return True

def register_history_write(self,vals):
    for brw_each in self:
        if vals:
            self.env["log.history"].register(self._name,brw_each.id,_("REGISTRO ACTUALIZADO"),"updated",vals,brw_each[self._rec_name]) 
    return True

def register_history_create(self,vals):
    self.env["log.history"].register(self._name,self.id,_("REGISTRO CREADO"),"created",vals,self[self._rec_name])
    return True

setattr(InheritBaseModel, "register_history_create", register_history_create)
setattr(InheritBaseModel, "register_history_write", register_history_write)
setattr(InheritBaseModel, "register_history_unlink", register_history_unlink)