# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models, _
from .. import  MODULE_NAME
from ..tools import FileManager
fileObj=FileManager()
import logging
_logger = logging.getLogger(__name__)
from lxml import etree

icons={
        "info":"information",
        "information":"information",
        "default":"information",
        "idea":"idea",
        "error":"error",
        "question":"question",
        "warning":"warning",
        "locked":"locked",
        "unlocked":"unlocked",
        "file":"file"
        }

class MessageWizard(models.TransientModel):
    _name="message.wizard"
    _description="Asistente de Mensajes"
    
    title=fields.Text("Título",required=False)
    name=fields.Text("Mensaje",required=False)
    
    @api.model
    def show(self,title,message,type="info",context=None):
        brw_create=self.create({"name":message,"title":title})   
        return self.env["ir.model.data"].sudo().invoke_wizard(self._name,brw_create.id,context)    
