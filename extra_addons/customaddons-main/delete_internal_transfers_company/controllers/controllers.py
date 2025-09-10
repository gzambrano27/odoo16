# -*- coding: utf-8 -*-
# from odoo import http


# class DeleteInternalTransfersCompany(http.Controller):
#     @http.route('/delete_internal_transfers_company/delete_internal_transfers_company', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/delete_internal_transfers_company/delete_internal_transfers_company/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('delete_internal_transfers_company.listing', {
#             'root': '/delete_internal_transfers_company/delete_internal_transfers_company',
#             'objects': http.request.env['delete_internal_transfers_company.delete_internal_transfers_company'].search([]),
#         })

#     @http.route('/delete_internal_transfers_company/delete_internal_transfers_company/objects/<model("delete_internal_transfers_company.delete_internal_transfers_company"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('delete_internal_transfers_company.object', {
#             'object': obj
#         })
