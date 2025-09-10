# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _
from odoo.models import BaseModel as InheritBaseModel
from odoo.exceptions import ValidationError

def execute_fx(self):
    context=self._context.copy()
    if not context.get("function",False):
        raise ValidationError(_("Función no definida"))
    OBJ_FUNCTION=self.env["dynamic.function"]    
    srch_function_ids= OBJ_FUNCTION.search([('active','=',True),('name','=',context["function"])])
    if srch_function_ids:
        brw_function=srch_function_ids[0]
        arguments=brw_function.arguments.split(",")
        if(arguments.__len__()!=2):
            raise ValidationError(_("Esta función debe tener dos argumentos 'self' y 'context'"))
        localdict=OBJ_FUNCTION.execute(brw_function.programming_code,{"self":self,"context":context})
        return localdict.get("result",True)
    raise ValidationError(_("Función no encontrada"))


setattr(InheritBaseModel, "execute_fx", execute_fx)