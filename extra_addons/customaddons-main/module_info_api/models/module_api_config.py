# module_info_api/models/module_api_config.py
# -*- coding: utf-8 -*-
import uuid
from odoo import models, fields, api

class ModuleApiConfig(models.Model):
    _name = 'module.api.config'
    _description = 'Configuración API de Módulo'

    name = fields.Char('Nombre', required=True)
    module_id = fields.Many2one(
        'ir.model', string='Módulo', required=True,
        ondelete='cascade',
    )
    access_token = fields.Char(
        'Token de Acceso', readonly=True, copy=False,
        default=lambda self: uuid.uuid4().hex
    )
    api_endpoint = fields.Char(
        'API Endpoint', readonly=True,
        compute='_compute_api_endpoint',
        help='URL para obtener los datos configurados'
    )
    field_ids = fields.One2many(
        'module.api.field', 'config_id', string='Campos'
    )
    dominio = fields.Text(
        string='Filtro/Dominio',
        help='Dominio en formato JSON que se aplicará al buscar los registros del módulo. Ejemplo: [["state", "=", "done"]]'
    )
    
    @api.depends('module_id', 'access_token')
    def _compute_api_endpoint(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url').rstrip('/')
        for rec in self:
            if rec.module_id and rec.access_token:
                m = rec.module_id.model
                # Nuevo formato: /api/v1/<m>/data?token=<token>
                rec.api_endpoint = f"{base}/api/v1/{m}/data?token={rec.access_token}"
            else:
                rec.api_endpoint = ''


class ModuleApiField(models.Model):
    _name = 'module.api.field'
    _description = 'Campo API de Módulo'

    config_id = fields.Many2one(
        'module.api.config', string='Configuración',
        ondelete='cascade', required=True
    )
    parent_module_id = fields.Many2one(
        'ir.model', related='config_id.module_id',
        store=True, readonly=True
    )
    model_id = fields.Many2one(
        'ir.model.fields', string='Campo (Model.Field)', required=True,
        ondelete='cascade',
        domain="[('model_id.model','ilike', parent_module_id.model + '.%')]"
    )
    name_alias = fields.Char('Alias', required=True)
