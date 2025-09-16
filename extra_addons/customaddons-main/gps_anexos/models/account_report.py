# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import datetime
import io
import json
import logging
import math
import re
import base64
from ast import literal_eval
from collections import defaultdict
from functools import cmp_to_key

import markupsafe
from babel.dates import get_quarter_names
from dateutil.relativedelta import relativedelta

from odoo.addons.web.controllers.utils import clean_action
from odoo import models, fields, api, _, osv
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import config, date_utils, get_lang, float_compare, float_is_zero
from odoo.tools.float_utils import float_round
from odoo.tools.misc import formatLang, format_date, xlsxwriter
from odoo.tools.safe_eval import expr_eval, safe_eval
from odoo.models import check_method_name

_logger = logging.getLogger(__name__)
import io
import shutil
import tempfile
import xlrd
import xlwt
from openpyxl import Workbook
from odoo import modules


class AccountReport(models.Model):

    _inherit = 'account.report'

    report_action_id = fields.Many2one(
        comodel_name='ir.actions.report',
        string='Reporte de Presupuesto'
    )

class GenericTaxReportCustomHandler(models.AbstractModel):
    _inherit = 'account.generic.tax.report.handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['buttons'].append({'name': _('Generar Archivo'), 'action': 'action_generate_xlsx_file', 'sequence': 80})

    def action_generate_xlsx_file(self, options):
        #print(options)
        report_id = options.get('report_id')
        brw_report = self.env['account.report'].browse(report_id)
        if not brw_report in (self.env.ref('l10n_ec.tax_report_104'),
                              self.env.ref('l10n_ec.tax_report_103')):
            raise ValidationError(_("Esta opcion no esta disponible para reportes diferentes al anexo 103  y 104"))
        #if not brw_report.report_action_id:
        return self.export_to_report_action(brw_report,options)
        #return self.export_to_xlsx(options)

    def export_to_report_action(self, report, options):
        # 5️⃣ Agregar tus datos dinámicos (ejemplo fila 60 en Excel, fila 59 índice 0)


        allowed_company_ids = self._context.get('allowed_company_ids', [])
        brw_company=self.env["res.company"].sudo().browse(allowed_company_ids[0])
        date_to = options.get('date', {}).get('date_to')
        anio, mes, _ = date_to.split('-')
        raw_lines = report._get_lines(options)
        self._cr.execute("select value,name from calendar_month " )
        dct_mes=dict(self._cr.fetchall())
        result=[{
            "ky_id": "name",
            "dscr": "company_name",
            "value": brw_company.name,
            "cell_row": "A1"
            },
            {
                "ky_id": "name",
                "dscr": "period_name",
                "value": ("%s DEL %s" % (dct_mes[int(mes)],anio)).upper(),
                "cell_row": "A3"
            }
            # {
            #     "ky_id": "vat",
            #     "dscr": "company_vat",
            #     "value": brw_company.vat,
            #     "cell_row": None
            # },
            # {
            #     "ky_id": "year",
            #     "dscr": "year",
            #     "value":anio,
            #     "cell_row": None
            # },
            # {
            #     "ky_id": "mes",
            #     "dscr": "mes",
            #     "value":mes,
            #     "cell_row":None
            # }
        ]
        for line in raw_lines:
            report_line_id = int(self._get_column_value(line, index=0, field_ky="report_line_id") or 0)
            if report_line_id:
                brw_report_line = self.env["account.report.line"].sudo().browse(report_line_id)
                ky_id = line.get('id')
                dscr = line.get('name')
                value = self._get_column_value(line,index= 0,field_ky="no_format")
                if brw_report_line.cell_report:
                    result.append({
                        "ky_id":ky_id,
                        "dscr": dscr,
                        "value": value,
                        "cell_row":brw_report_line.cell_report
                    })
        return report.report_action_id.report_action(self, data={'result': result})

    def _get_column_value(self, line, index=0,field_ky="name"):
        try:
            raw = line["columns"][index][field_ky]
            #print(raw)
            return raw
        except (IndexError, KeyError, ValueError, TypeError):
            return 0.0
