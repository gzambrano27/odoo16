# -*- coding: utf-8 -*-
# © <2024> <Washington Guijarro>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import (
    api,
    models,
    fields,
    _
)
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError
from datetime import datetime, date, time, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_is_zero, float_compare

class AccountAnalyticAccount(models.Model):

    _inherit = 'account.analytic.account'
    
    descripcion = fields.Char('Descripcion')
    ubicaciones_id = fields.Many2one('centro.costo.ubicaciones', 'Ubicacion')
    tipo_proy_id = fields.Many2one('centro.costo.tipo.proyecto','Tipo Proyecto')
    zona_id = fields.Many2one('centro.costo.zona','Zona Referencia')
    nro_contrato = fields.Char('Nro. Contrato')
    nombre_proyecto = fields.Char('Nom Proy')
    nombre_proyecto_id = fields.Many2one('centro.costo.nombre.proyecto','Nombre Proyecto')
    
#     @api.model
#     def create(self,vals):
#         print vals
#         if vals['name']:
#             vals['name']=vals['name']
#         res = super(AccountAnalyticAccount, self).create(vals)
#     return res
#  
#     @api.multi
#     def write(self,vals):
#         if not self.name:
#             vals['name'] = self.name
#         res = super(AccountAnalyticAccount, self).write(vals)
#     return res 
    
    # def name_get(self):
    #     res = []
    #     for analytic in self:
    #         name = analytic.name
    #         if analytic.code and analytic.tipo_proy_id:
    #             name = analytic.code+' - '+analytic.tipo_proy_id.name+' '+analytic.descripcion#+' '+name
    #         if analytic.partner_id:
    #             name = name +' - '+analytic.partner_id.commercial_partner_id.name +analytic.tipo_proy_id.name+' '+analytic.descripcion
    #         res.append((analytic.id, name))
    #     return res
    
    @api.onchange('zona_id')
    def changezona(self):
        res={}
        if self.zona_id:
            res['descripcion'] = self.zona_id.name
        return {'value':res}
    
    @api.onchange('code','tipo_proy_id','name','descripcion')
    def onchange_name(self):
        values={}
        res = ''
        if self.code and self.tipo_proy_id and self.descripcion:
            values['name']='['+self.code+'] '+self.tipo_proy_id.name+' '+self.descripcion
        return {'value':values}
    
    