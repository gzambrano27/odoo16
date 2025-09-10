# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models,_
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import ValidationError

class WorkflowHistory(models.Model):    
    _name="workflow.history"
    _description="Log de Cambios de Estado"
    
    def compute_style(self):
        context=self._context
        bold_tag=context.get('bold_tag',[])
        it_tag=context.get('it_tag',[])
        for brw_each in self:
            brw_each.bold_flag=(brw_each.state in bold_tag)
            brw_each.it_flag=(brw_each.state in it_tag)
            brw_each.color_flag=context.get('tag_'+brw_each.state,'black')
            
    state=fields.Selection([],string="Estado",required=True)
    comments=fields.Text("Comentario",required=False)
    file=fields.Binary("Archivo",required=False,attachment=True)
    file_name=fields.Char("Nombre de Archivo",required=False,size=255)
    bold_flag=fields.Boolean(compute="compute_style",string="Negrita",default=False)
    it_flag=fields.Boolean(compute="compute_style",string="Cursiva",default=False)
    color_flag=fields.Selection([('muted','Plomo'),('danger','Rojo'),('success','Verde'),('primary','Morado'),('info','Azul'),('warning','Marrón'),('black','Negro')],compute="compute_style",string="Color",default='black')
     
    @api.model
    def register(self,parent_id,comments,state,file=False,file_name=False):  
        if ((not file and file_name) or (file and not file_name)):
            raise ValidationError(_("Nombre de Archivo y Archivo son requeridos"))        
        self.create({"parent_id":parent_id,
                     "comments":comments,
                     "state":state,
                     "file":file,
                     "file_name":file_name
                     })
        return True
    
    _order="id desc"
    
