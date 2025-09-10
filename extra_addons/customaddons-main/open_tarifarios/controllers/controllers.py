# -*- coding: utf-8 -*-
# from odoo import http


# class OpenTarifarios(http.Controller):
#     @http.route('/open_tarifarios/open_tarifarios', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/open_tarifarios/open_tarifarios/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('open_tarifarios.listing', {
#             'root': '/open_tarifarios/open_tarifarios',
#             'objects': http.request.env['open_tarifarios.open_tarifarios'].search([]),
#         })

#     @http.route('/open_tarifarios/open_tarifarios/objects/<model("open_tarifarios.open_tarifarios"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('open_tarifarios.object', {
#             'object': obj
#         })
