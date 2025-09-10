# -*- coding: utf-8 -*-
from odoo import models, fields, api,SUPERUSER_ID,_
import io
import xlsxwriter
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError,ValidationError
from odoo.http import content_disposition, request

class SecurityGroupWizard(models.TransientModel):
    _name = "security.group.wizard"
    _description="Asistente para consultar Info. de Seguridad"

    menu_ids=fields.Many2many("ir.ui.menu","security_group_wizard_menu_rel","wizard_id","menu_id","Menus",required=True)

    def process(self):
        self = self.with_context({"no_raise": True})
        self = self.with_user(SUPERUSER_ID)
        REPORT = "gps_reports.menu_group_report_xlsx_act"
        for brw_each in self:
            try:
                # brw_each.validate_range_days()
                OBJ_REPORTS = self.env[self._name].sudo()
                context = dict(active_ids=[brw_each.id],
                               active_id=brw_each.id,
                               active_model=self._name,
                               landscape=True
                               )
                OBJ_REPORTS = OBJ_REPORTS.with_context(context)
                report_value = OBJ_REPORTS.env.ref(REPORT).with_user(SUPERUSER_ID).report_action(OBJ_REPORTS)
                report_value["target"] = "new"
                return report_value
            except Exception as e:
                raise ValidationError(_("Error al Imprimir %s -- %s") % (REPORT, str(e),))