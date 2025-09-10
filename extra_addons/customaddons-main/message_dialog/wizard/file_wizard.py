# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models, _

class FileWizard(models.TransientModel):
    _name="file.wizard"
    _inherit="message.wizard"
    _description="Asistente para descargas de Archivos"
    
    file=fields.Binary("Archivo",required=True)
    file_name=fields.Char("Nombre de Archivo",required=True,size=255)
    
    @api.model
    def download(self,title,message,file,file_name,context=None):
        brw_create=self.create({"name":message,"title":title,"file":file,"file_name":file_name})        
        return {
                     'type' : 'ir.actions.act_url',
                     'url': '/web/content/%s/%s/file/%s' % (self._name,
                                                                brw_create.id,
                                                                file_name),
                     'target': 'new'
            }
