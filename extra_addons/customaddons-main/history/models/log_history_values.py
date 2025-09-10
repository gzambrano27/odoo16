# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models,_
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)
from odoo.tools.safe_eval import safe_eval,_BUILTINS

class LogHistoryValues(models.Model):    
    _name="log.history.values"
    _description="Valores del Historial de Modificaciones"
        
    def _get_field(self):        
        for brw_each in self:
            fields_ids=self.env["ir.model.fields"].search([("model_id.model","=",brw_each.log_history_id.model_name),("name","=",brw_each.field_name)])
            brw_each.field_id=fields_ids and fields_ids[0] or False
            brw_each.has_childs=(brw_each.child_ids.__len__()>0)
            
    log_history_id=fields.Many2one("log.history","Historia",ondelete="cascade")
    field_name=fields.Char("Clave",size=255,required=True)
    field_string=fields.Char("Descripción",size=255)
    value=fields.Text("Valor")
    field_id=fields.Many2one("ir.model.fields", "Campo",compute='_get_field')
    has_childs=fields.Boolean(string="Tiene hijo(s)",compute='_get_field')
    parent_id=fields.Many2one("log.history.values", "Registro Padre")
    child_ids=fields.One2many("log.history.values","parent_id","Registro(s) Hijo(s)")
    state=fields.Selection([('set','Asignado'),('created','Creado'),('updated','Actualizado'),('unlinked','Borrado')],string="Estado",default="set",required=False)
    
    _order="field_name asc" 
    
    @api.model
    def _m2o(self,model,resource_id):
        OBJ_MODEL=self.env[model]
        rec_name=OBJ_MODEL._rec_name
        brw_model=OBJ_MODEL.browse(resource_id)
        try:
            return brw_model[rec_name] and str(brw_model[rec_name]) or ""
        except:
            return str(_("REGISTRO DESCONOCIDO,%s")) % (resource_id,)
    
    def _t(self,value):
        lang=self._context.get('lang','es_EC')
        new_value= _(value)
        if(value!=new_value):
            return new_value
        return new_value
#         self._cr.execute("""SELECT X.VALUE
# FROM IR_TRANSLATION X
# WHERE X.LANG='{}' 
# AND X.STATE='translated' AND X.SRC='{}' """.format(lang,value))
#         result=self._cr.fetchone()
#         if not result:
#             return value
#         return (result[0] is None or not result[0]) and result[0] or value
        
    @api.model
    def __get_event_values (self,model,arguments):
        def merge_columns(inherits,columns):
            if type(inherits)==str:
                inherits=[inherits]
            if inherits:
                for each_model_inherit in inherits:
                    OBJ_INHERIT=self.env[each_model_inherit]
                    columns.update(OBJ_INHERIT._fields.copy())
            return columns
        def list_empty():
            return str("***")
        def clear_list_empty(str_value):
            return str(str_value.replace("***,", "").replace("***", ""))
        def format_one2many(dscr,id):
            return "%s,%s" % (dscr,id)
        localdict={}
        locals_builtins=_BUILTINS.copy()
        locals_builtins["datetime"]=datetime
        safe_eval("result = {}".format(arguments), globals_dict=locals_builtins, locals_dict=localdict, mode="exec", nocopy=True, locals_builtins=locals_builtins)
        compute_params = localdict.get("result",{})
        OBJ_MODEL=self.env[model]
        COLUMNS=OBJ_MODEL._fields.copy()
        list_inherits=OBJ_MODEL._inherits
        if(type(list_inherits)==dict):
            list_inherits=OBJ_MODEL._inherits.keys()
        COLUMNS=merge_columns(list_inherits,COLUMNS)
        if getattr(OBJ_MODEL, "_inherit",False):
            list_inherit=OBJ_MODEL._inherit
            if(type(list_inherit)==str):
                list_inherit=[OBJ_MODEL._inherit]
            COLUMNS=merge_columns(list_inherit,COLUMNS)
        COLUMNS_CHECK=COLUMNS.keys()
        only_dict_values=compute_params        
        if(type(only_dict_values)==list):
            only_dict_values=only_dict_values[0]#dict
        compute_params=only_dict_values
        new_values=[]
        for each_param in compute_params.keys():
            field_string=_("Campo desconocido")
            value=compute_params[each_param]
            if each_param in COLUMNS_CHECK:
                field_string=str(COLUMNS[each_param].string)
                type_column= COLUMNS[each_param].type
                childs=[(5,)]
                state="set"
                if type_column in ("int","float"):
                    value=str(value)
                if type_column in ("char","text"):
                    pass
                if type_column in ("boolean"):
                    value=value and _("Si") or _("No")
                if type_column in ("date","datetime"):
                    value=value and str(value) or ""
                if type_column in ("many2one"):
                    value=self._m2o(COLUMNS[each_param].comodel_name, value)
                if type_column in ("selection"):
                    values_select={}
                    if type(COLUMNS[each_param].selection)==list:
                        values_select=dict(COLUMNS[each_param].selection)
                        value=self._t(values_select.get(value,value))
                    else:
                        values_select=dict(COLUMNS[each_param].selection(self.env[model]))
                        value=self._t(values_select.get(value,value))
                if type_column in ("many2many"):
                    list_display=list_empty()
                    CONMODEL_NAME=COLUMNS[each_param].comodel_name
                    for each_append in value:
                        if each_append[0]==6:
                            for each_value in each_append[2]:
                                list_display+=","+self._m2o(CONMODEL_NAME, each_value)
                    value=clear_list_empty(list_display)
                if type_column in ("one2many"):
                    list_display=list_empty()
                    CONMODEL_NAME=COLUMNS[each_param].comodel_name
                    if value:
                        for each_value in value:
                            if each_value:
                                if(each_value==(5,)):
                                    value=_("REGISTRO(S) ACTUALIZADO(S)")                        
                                if each_value.__len__()==3:
                                    if each_value[0] in (0,1): 
                                        new_value=_("CREADO")
                                        if(each_value[1]!=0):                                            
                                            new_value=format_one2many( _("ACTUALIZADO"),each_value[1])
                                        new_state=(each_value[1]==0) and 'created' and 'updated'
                                        new_childs=[(5,)]  
                                        values_o2m=self.__get_event_values(CONMODEL_NAME, str(each_value[2]))
                                        if values_o2m:
                                            if type(values_o2m)==list:
                                                for each_value_dict in values_o2m:
                                                    new_childs.append((0,0,each_value_dict))
                                        childs.append((0,0,{"field_name":"id",
                                                            "field_string":"ID",
                                                            "value":new_value,
                                                            "child_ids":new_childs,
                                                            "state":new_state
                                                            }))
                                    if each_value[0] in (2,3,4):
                                        dscr=_("ELIMINADO")
                                        new_state='unlinked'
                                        if(each_value[0]==3):
                                            dscr=_("DESREFERENCIADO")
                                            new_state='set' 
                                        if(each_value[0]==4):
                                            dscr=_("REFERENCIADO")   
                                            new_state='set'                                     
                                        childs.append((0,0,{"field_name":"id",
                                                            "field_string":"ID",
                                                            "value":format_one2many(dscr,each_value[1]),
                                                            "state":new_state
                                                            }))
                    value=_("REGISTRO(S) ACTUALIZADO(S)")  
                if type_column in ("binary"):
                    value=value and _("Archivo") or _("Archivo vacio")
                if not value:
                    value=""
                vals={"field_name":each_param,
                      "field_string":self._t(field_string),
                      "value":value,
                      "child_ids":childs,
                      "state":state}
                new_values.append(vals)
        return new_values
    
    @api.model
    def update_event_values(self,log_history_id,log_values):
        brw_value_ids=self.search([("log_history_id","=",log_history_id)])
        if brw_value_ids:
            brw_value_ids.unlink()
        brw_history=self.env["log.history"].browse(log_history_id)
        model_name=brw_history.model_name
        new_record_ids=[]
        new_values=self.__get_event_values(model_name, log_values)            
        for each_vals in new_values:
            each_vals["log_history_id"]=log_history_id
            new_record_ids.append(self.create(each_vals).id)            
        return new_record_ids
