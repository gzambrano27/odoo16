# -*- coding: utf-8 -*-
# from odoo import http


# class ImportOc(http.Controller):
#     @http.route('/import_oc/import_oc', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/import_oc/import_oc/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('import_oc.listing', {
#             'root': '/import_oc/import_oc',
#             'objects': http.request.env['import_oc.import_oc'].search([]),
#         })

#     @http.route('/import_oc/import_oc/objects/<model("import_oc.import_oc"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('import_oc.object', {
#             'object': obj
#         })
