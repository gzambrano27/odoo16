from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class PowerBIDashboard(models.Model):
    _name = 'powerbi.dashboard.gen'
    _description = 'Power BI Dashboard'

    name = fields.Char("Título", required=True)
    category = fields.Selection([
        ('sales', 'Ventas'),
        ('crm', 'CRM'),
        ('finance', 'Finanzas'),
        ('logistics', 'Logística/Supply'),
        ('project', 'Proyectos'),
        ('hr', 'Talento Humano'),
    ], string="Categoría", required=True)
    embed_url = fields.Char("Power BI Embed URL", required=True)
    show_iframe = fields.Boolean(string="Mostrar iframe", default=False)
    report_html = fields.Html(string='Vista previa', compute='_compute_report_html', sanitize=False)
    custom_code = fields.Text(string='Código Python (HTML)')

    # @api.depends('category', 'embed_url')
    # def _compute_report_html(self):
    #     for rec in self:
    #         if rec.category == 'sales':
    #             rec.report_html = f'''
    #                 <iframe title="Seguimiento Compras Proyectos"
    #                         width="600" height="373.5"
    #                         src="{rec.embed_url or ''}"
    #                         frameborder="0" allowFullScreen="true"></iframe>
    #             '''
    #         elif rec.category == 'finance':
    #             rec.report_html =  f'''
    #                 <iframe title="Seguimiento Finanzas"
    #                         width="600" height="373.5"
    #                         src="{rec.embed_url or ''}"
    #                         frameborder="0" allowFullScreen="true"></iframe>
    #             '''
    #         else:
    #             rec.report_html = '<em style="color:gray;">No se ha definido una categoría para mostrar el informe.</em>'

    @api.depends('custom_code', 'category', 'embed_url')
    def _compute_report_html(self):
        for rec in self:
            localdict = {
                'category': rec.category,
                'embed_url': rec.embed_url or '',
            }
            try:
                if rec.custom_code:
                    exec(rec.custom_code, {}, localdict)
                    rec.report_html = localdict.get('result', '<em style="color:gray;">No se ha definido resultado en la variable <strong>result</strong>.</em>')
                else:
                    rec.report_html = '<em style="color:gray;">No se ha definido código.</em>'
            except Exception as e:
                rec.report_html = f'<div style="color:red;">Error en código:<br/>{str(e)}</div>'
                _logger.error(f"[PowerBI Dashboard] Error evaluando código: {e}")

    def action_show_iframe(self):
        self.ensure_one()
        self.show_iframe = True
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'powerbi.dashboard.gen',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # group_ids = fields.Many2many(
    #     'res.groups',
    #     string="Visible para Grupos",
    #     help="Solo los usuarios que pertenezcan a estos grupos podrán ver este dashboard."
    # )
