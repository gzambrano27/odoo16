# -*- coding: utf-8 -*-
# from odoo import http


# class TalentHuman(http.Controller):
#     @http.route('/talent_human/talent_human', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/talent_human/talent_human/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('talent_human.listing', {
#             'root': '/talent_human/talent_human',
#             'objects': http.request.env['talent_human.talent_human'].search([]),
#         })

#     @http.route('/talent_human/talent_human/objects/<model("talent_human.talent_human"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('talent_human.object', {
#             'object': obj
#         })
