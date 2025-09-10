# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class TemplateReportsHtml(models.Model):
    _name = 'template.reports.html'
    _description = 'Template Reports HTML'

    name = fields.Char(string='Nombre')
    description = fields.Text(string='Descripción')
    python_code = fields.Text(string='Código Python')
    html = fields.Html(string='HTML')
    active = fields.Boolean(string='Activo', default=True)

    # def action_view_html(self):
    #     return {
    #         'name': _('HTML'),
    #         'type': 'ir.actions.act_url',
    #         'url': '/web/content/%s/html' % self.id,
    #         'target': 'new',
    #     }

    # def action_view_pdf(self):
    #     return {
    #         'name': _('PDF'),
    #         'type': 'ir.actions.act_url',
    #         'url': '/web/content/%s/pdf' % self.id,
    #         'target': 'new',
    #     }

    # def action_view_odt(self):
    #     return {
    #         'name': _('ODT'),
    #         'type': 'ir.actions.act_url',
    #         'url': '/web/content/%s/odt' % self.id,
    #         'target': 'new',
    #     }

    # def action_view_docx(self):
    #     return {
    #         'name': _('DOCX'),
    #         'type': 'ir.actions.act_url',
    #         'url': '/web/content/%s/docx' % self.id,
    #         'target': 'new',
    #     }

    # def action_view_xlsx(self):
    #     return {
    #         'name': _('XLSX'),
    #         'type': 'ir.actions.act_url',
    #         'url': '/web/content/%s/xlsx' % self.id,
    #         'target': 'new',
    #     }

    # def action_view_pptx(self):
    #     return {
    #         'name': _('PPTX'),
    #         'type': 'ir.actions.act_url',
    #         'url': '/web/content/%s/pptx' % self.id,
    #         'target': 'new',
    #     }

    # def action_view_image(self):
    #     return {
    #         'name': _('Image'),
    #         'type': 'ir.actions.act_url',
    #         'url': '/web/content/%s/image' % self.id,
    #         'target': 'new',
    #     }

    # def action_view_video(self):
    #     return {
    #         'name': _('Video'),
    #         'type': 'ir.actions.act_url',
    #         'url': '/web/content/%s/video' % self.id,
    #         'target': 'new',
    #     }

    # def action_view_audio(self):
    #     return {
    #         'name': _('Audio'),
    #         'type': 'ir.actions.act_url',
    #         'url': '/web/content/%s/audio' % self.id,
    #         'target': 'new',
    #     }

# class template_html_reports(models.Model):
#     _name = 'template_html_reports.template_html_reports'
#     _description = 'template_html_reports.template_html_reports'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
