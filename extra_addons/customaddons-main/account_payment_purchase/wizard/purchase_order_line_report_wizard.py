# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _,SUPERUSER_ID
from ...message_dialog.tools import FileManager
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager
fileO=FileManager()
dateO=DateManager()
calendarO=CalendarManager()
from datetime import timedelta

class PurchaseOrderLineReportWizard(models.TransientModel):
    _name="purchase.order.line.report.wizard"
    _description="Asistente de reportes de ordenes de compra"

    @api.model
    def get_default_company_ids(self):
        if self._context.get("allowed_company_ids", []):
            return self._context.get("allowed_company_ids", [])
        return [self.env["res.users"].browse(self._uid).company_id.id]

    company_ids = fields.Many2many("res.company", "purchase_order_line_wizard_report_comp_rel", "wizard_id",
                                   "company_id", "Compañias", default=get_default_company_ids)

    @api.model
    def get_default_date_from(self):
        return fields.Date.context_today(self) + timedelta(days=-30)

    @api.model
    def get_default_date_to(self):
        return fields.Date.context_today(self)

    date_from = fields.Date(string="Desde", default=get_default_date_from)
    date_to = fields.Date(string="Hasta", default=get_default_date_to)

    def process(self):
        self.ensure_one()
        srch=self.env["purchase.order"].sudo().search([
            ('company_id','in',self.company_ids.ids),
            ('date_order','>=',self.date_from),
            ('date_order','<=',self.date_to),
            ('state','!=','cancel')
        ])
        if not srch:
            raise ValidationError(_("No hay registros con estos criterios"))
        srch=srch.with_context({"with_precio_venta":True})
        return srch.action_view_margen()
