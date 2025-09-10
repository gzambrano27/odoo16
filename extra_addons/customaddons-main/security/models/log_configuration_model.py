# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import SUPERUSER_ID,api,fields, models,_
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class LogConfigurationModel(models.Model):    
    _name="log.configuration.model"
    _description="Configuración de Log de Modificaciones"
    
    model_id=fields.Many2one("ir.model","Módelo",ondelete="cascade")
    name=fields.Char(related="model_id.model",string="Objeto",store=False,readonly=True)
    on_create=fields.Boolean("Crear",default=True)
    on_write=fields.Boolean("Actualizar",default=True)
    on_unlink=fields.Boolean("Eliminar",default=True)
    locked=fields.Boolean("Bloqueado",default=False)
    
    _sql_constraints = [("log_config_model_unique_model","unique(model_id)",",Módelo debe ser única"),]
    
    @api.onchange('model_id')
    def onchange_model_id(self):
        self.name=None
        if self.model_id:
            self.name=self.model_id.model
            
    def unlink(self):
        for brw_each in self:
            if brw_each.locked:
                raise UserError(_("Registro esta bloqueado no puede ser borrado"))
        return super(LogConfigurationModel,self).unlink()
        
    @api.model
    def create(self, vals):
        brw_new= super(LogConfigurationModel,self).create(vals)       
        return brw_new
    
    def write(self, vals):    
        value= super(LogConfigurationModel,self).write(vals)
        return value
    
    _rec_name="model_id"
    
