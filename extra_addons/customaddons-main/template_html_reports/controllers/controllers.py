# -*- coding: utf-8 -*-
# from odoo import http


# class TemplateHtmlReports(http.Controller):
#     @http.route('/template_html_reports/template_html_reports', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/template_html_reports/template_html_reports/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('template_html_reports.listing', {
#             'root': '/template_html_reports/template_html_reports',
#             'objects': http.request.env['template_html_reports.template_html_reports'].search([]),
#         })

#     @http.route('/template_html_reports/template_html_reports/objects/<model("template_html_reports.template_html_reports"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('template_html_reports.object', {
#             'object': obj
#         })
