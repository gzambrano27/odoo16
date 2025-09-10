# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2016-2017 Lajonner Crespin & Dalemberg Crespin
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import api,fields, models,_

class DynamicFunctionTestWizard(models.TransientModel):
    
    _name="dynamic.function.test.wizard"
    _description="Asistente de Ejecucion de Funciones"
    
    @api.model
    def __get_dynamic_id(self):
        return self._context.get("active_id",False)
    
    @api.model
    def __get_name(self):
        if self._context.get("active_id",False):
            OBJ_DYNAMIC=self.env["dynamic.function"]
            brw_dynamic=OBJ_DYNAMIC.browse(self._context["active_ids"][0])
            return brw_dynamic.displayed_name
        return ""
    
    dynamic_id=fields.Many2one("dynamic.function","Función",required=False,default=__get_dynamic_id)
    name=fields.Char("Definición",required=False,size=255,default=__get_name)
    arguments=fields.Text("Argumentos",required=False)
    required_arguments=fields.Boolean("Requiere Argumentos")
    
    @api.onchange('dynamic_id')
    def onchange_dynamic_id(self):
        if self.dynamic_id:
            brw_function=self.dynamic_id
            return {"value":{"name":brw_function.displayed_name,
                             "arguments":brw_function.arguments and brw_function.arguments or "",
                             "required_arguments":brw_function.arguments and True or False}}
        return {"value":{"name":"","arguments":"","required_arguments":False}}
    
    def process(self):
        for brw_each in self:
            OBJ_DYNAMIC=self.env["dynamic.function"]
            arguments=""
            if brw_each.arguments:
                arguments+=brw_each.arguments
            programming_code="result=["+arguments+"]"
            localdict={}
            localdict=OBJ_DYNAMIC.execute(programming_code,{})
            variable_list=localdict.get("result",[])
            value=localdict[brw_each.dynamic_id.name](*variable_list)
            return localdict["message"](_("Resultado"),value)            
        return True
    
