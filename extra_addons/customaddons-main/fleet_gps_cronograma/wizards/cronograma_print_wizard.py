# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class CronogramaPrintWizard(models.TransientModel):
    _name = "cronograma.print.wizard"
    _description = "Fechas a Imprimir"

    # ───────────────────────────────────────── fields
    date_start = fields.Date(string="Desde", required=True,
                             default=fields.Date.context_today)
    date_end   = fields.Date(string="Hasta")

    # ───────────────────────────────────────── onchange
    @api.onchange("date_start")
    def _onchange_date_start(self):
        """Al elegir la fecha de inicio se proponen 7 días (editable)."""
        if self.date_start:
            self.date_end = self.date_start + relativedelta(days=6)

    # ───────────────────────────────────────── actions
    def action_print(self):
        """Lanza el informe PDF usando el rango indicado."""
        self.ensure_one()

        # Registros a mostrar (los filtramos por fecha)
        docs = self.env["fleet.cronograma"].sudo().search([
            ("necesidad_entrega", ">=", self.date_start),
            ("necesidad_entrega", "<=", self.date_end),
        ])

        # Lista con los 7 días de cabecera (formato ISO para pasarlos por JSON)
        days = [
            (self.date_start + relativedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(7)
        ]

        action = self.env.ref("fleet_gps_cronograma.action_report_cronograma")
        return action.report_action(
            docs.ids,                 # docids
            data={
                "date_start": fields.Date.to_string(self.date_start),
                "date_end"  : fields.Date.to_string(self.date_end),
                "days"      : days,   # cabecera
            },
        )
