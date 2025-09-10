# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models,_
import logging
_logger = logging.getLogger(__name__)

class LogHistory(models.Model):    
    _name="log.history"
    _description="Historial de Log de Modificaciones"
    
    def _get_childs(self):        
        for brw_each in self:
            brw_each.has_childs=(brw_each.values_ids.__len__()>0)
            
    state=fields.Selection([('created','Creado'),('updated','Actualizado'),('unlinked','Borrado')],string="Estado",default="created",required=True)
    comments=fields.Text("Comentario",required=False)
    model_name=fields.Char("Modelo",size=255,required=True)
    model_id=fields.Integer("ID Modelo",required=True)
    name=fields.Char("Nombre",required=True)
    log_values=fields.Text("Valores")
    values_ids=fields.One2many("log.history.values", "log_history_id", "Valor(es)")    
    has_childs=fields.Boolean(string="Tiene Registro(s)",compute='_get_childs')
    
    @api.model
    def register(self,model_name,model_id,comments,state,log_values={},name=None):
        if 'write_date' in log_values:
            if log_values['write_date']:
                del log_values['write_date']
        self.create({"model_name":model_name,
                     "model_id":model_id,
                     "comments":comments,
                     "state":state,
                     "name":((name is None) or (not name)) and (("%s,%s") % (model_name,model_id)) or name,
                     "log_values":log_values and str(log_values) or "{}"
                     })
        return True
    
    def unlink(self):
        raise models.UserError(_("Registro no puede ser eliminado"))
    
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        raise models.UserError(_("Registro no puede ser duplicado"))
    
    def read(self, fields=None, load='_classic_read'):
        read_values=super(LogHistory,self).read(fields, load)
        if (len(self._ids)==1):
            for each_values in read_values:
                if("values_ids" in each_values):
                    new_value_ids=self.env["log.history.values"].update_event_values(each_values["id"],each_values.get("log_values","{}"))
                    each_values["values_ids"]=new_value_ids
        return read_values
    
    _order="state desc,id desc"
    
