# module_info_api/controllers/module_info_controller.py
# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request

class ModuleInfoController(http.Controller):
    @http.route('/api/v1/configs', type='http', auth='public', methods=['GET'], csrf=False)
    def list_configs(self, **kwargs):
        """Devuelve la lista de configuraciones disponibles."""
        configs = request.env['module.api.config'].sudo().search([])
        data = configs.read(['id', 'name', 'module_id'])
        return request.make_response(
            json.dumps({'configs': data}, default=str),
            [('Content-Type', 'application/json')]
        )

    @http.route('/api/v1/configs/<int:config_id>', type='http', auth='public', methods=['GET'], csrf=False)
    def get_config(self, config_id, **kwargs):
        """Devuelve los detalles de una configuración específica."""
        config = request.env['module.api.config'].sudo().browse(config_id)
        if not config.exists():
            return request.make_response(
                json.dumps({'error': 'Configuración no encontrada'}, default=str),
                [('Content-Type', 'application/json')], status=404
            )
        result = {
            'id': config.id,
            'name': config.name,
            'module': config.module_id.model,
            'access_token': config.access_token,
            'api_endpoint': config.api_endpoint,
            'fields': [
                {'model': line.model_id.model, 'field': line.model_id.name}
                for line in config.field_ids
            ]
        }
        return request.make_response(
            json.dumps(result, default=str),
            [('Content-Type', 'application/json')]
        )

    @http.route('/api/v1/<string:module>/data', type='http', auth='public', methods=['GET'], csrf=False)
    def get_module_data(self, module, token=None, **kwargs):
        """Devuelve los registros del módulo, agrupando todos los campos solicitados."""
        Config = request.env['module.api.config'].sudo()
        config = Config.search([('module_id.model', '=', module)], limit=1)
        if not config:
            return request.make_response(
                json.dumps({'error': f'Configuración no encontrada para módulo {module}'}, default=str),
                [('Content-Type', 'application/json')], status=404
            )
        if token != config.access_token:
            return request.make_response(
                json.dumps({'error': 'Token inválido'}, default=str),
                [('Content-Type', 'application/json')], status=403
            )

        # Agrupar nombres de campos por modelo
        model_fields = {}
        for line in config.field_ids:
            model_name = line.model_id.model
            model_fields.setdefault(model_name, []).append(line.model_id.name)

        data = {}
        # Hacer una sola búsqueda por modelo con todos los campos
        for model_name, fields in model_fields.items():
            try:
                #records = request.env[model_name].sudo().search_read([], fields=fields)
                dominio_raw = kwargs.get('dominio') or config.dominio
                try:
                    domain = json.loads(dominio_raw) if dominio_raw else []
                    if not isinstance(domain, list):
                        raise ValueError()
                except Exception:
                    return request.make_response(
                        json.dumps({'error': 'El dominio debe ser una lista válida codificada en JSON. Ejemplo: [["state", "=", "done"]]'}, default=str),
                        [('Content-Type', 'application/json')], status=400
                    )

                # Buscar registros filtrados
                records = request.env[model_name].sudo().search_read(domain, fields=fields)
                data[model_name] = records
            except Exception as e:
                data[model_name] = {'error': str(e)}

        return request.make_response(
            json.dumps({
                'config': config.name,
                'module': module,
                'data': data
            }, default=str),
            [('Content-Type', 'application/json')]
        )
