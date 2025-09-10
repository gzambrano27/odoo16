# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _
from odoo import api
from odoo.models import BaseModel as InheritBaseModel
from odoo.exceptions import ValidationError

def match_history_action(self,field_value):
    model=self.env.get('log.configuration.model',False)
    if (type(model)!=bool):
        srch=model.sudo().search([('model_id.model','=',self._name)])
        if srch:
            for brw_each in srch:
                return brw_each[field_value]
    return False

setattr(InheritBaseModel, "match_history_action", match_history_action)

_old_create=InheritBaseModel.create
_old_write=InheritBaseModel.write
_old_unlink=InheritBaseModel.unlink

@api.model
@api.returns('self', lambda value: value.id)
def _new_create(self, vals):
    brw_new=_old_create(self,vals)
    if self.match_history_action("on_create"):
        brw_new.register_history_create(vals)  
    return brw_new

def _new_write(self, vals):
    value=_old_write(self,vals)
    if self.match_history_action("on_write"):
        self.register_history_write(vals) 
    return value

def _new_unlink(self):
    if self.match_history_action("on_unlink"):
        self.register_history_unlink() 
    value=_old_unlink(self)
    return value

setattr(InheritBaseModel, "create", _new_create)
setattr(InheritBaseModel, "write", _new_write)
setattr(InheritBaseModel, "unlink", _new_unlink)    