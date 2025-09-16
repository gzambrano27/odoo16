# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date

# --------------------------
# LÍNEAS DEL REPORTE (transient)
# --------------------------
class PrPoAnalyticReportLine(models.TransientModel):
    _name = "pr.po.analytic.report.line"
    _description = "Líneas Reporte PR ↔ PO (Distribución Analítica)"
    _order = "request_id, po_id, id"

    wizard_id = fields.Many2one("pr.po.analytic.report.wizard", ondelete="cascade", index=True)

    # Navegación / clic
    company_id = fields.Many2one("res.company", string="Compañía")
    request_id = fields.Many2one("purchase.request", string="Requisición")
    request_state = fields.Selection(
        selection=lambda self: self.env["purchase.request"]._fields["state"].selection,
        string="Estado PR",
    )

    po_id = fields.Many2one("purchase.order", string="Orden de Compra")
    po_state = fields.Selection(
        selection=lambda self: self.env["purchase.order"]._fields["state"].selection,
        string="Estado OC",
    )
    proveedor_id = fields.Many2one("res.partner", string="Proveedor")

    # Detalle producto / cantidades / montos
    product_code = fields.Char(string="Código")
    product_name = fields.Char(string="Producto")
    req_qty = fields.Float(string="Cant. Req.", digits="Product Unit of Measure")
    po_qty = fields.Float(string="Cant. OC", digits="Product Unit of Measure")

    company_currency_id = fields.Many2one("res.currency", related="company_id.currency_id", readonly=True)
    po_price_unit = fields.Monetary(string="Precio Unit.", currency_field="company_currency_id")
    po_price_subtotal = fields.Monetary(string="Subtotal", currency_field="company_currency_id")

    # Analítica
    analytic_account_id = fields.Many2one("account.analytic.account", string="Cuenta Analítica")
    analytic_percent = fields.Float(string="% Analítico", digits=(16, 4))
    analytic_client_id = fields.Many2one("res.partner", string="Cliente Analítico")

    # --- Trazabilidad (último cambio y contador) ---
    # PR
    pr_last_changed_on    = fields.Datetime("PR Fecha/Hora")
    pr_last_changed_by_id = fields.Many2one("res.users", string="PR Cambiado por")
    pr_last_state_from    = fields.Selection(selection=lambda s: s.env["purchase.request"]._fields["state"].selection, string="PR De")
    pr_last_state_to      = fields.Selection(selection=lambda s: s.env["purchase.request"]._fields["state"].selection, string="PR A")
    pr_last_note          = fields.Char("PR Nota")
    pr_log_count          = fields.Integer("PR #Cambios")

    # PO
    po_last_changed_on    = fields.Datetime("OC Fecha/Hora")
    po_last_changed_by_id = fields.Many2one("res.users", string="OC Cambiado por")
    po_last_state_from    = fields.Selection(selection=lambda s: s.env["purchase.order"]._fields["state"].selection, string="OC De")
    po_last_state_to      = fields.Selection(selection=lambda s: s.env["purchase.order"]._fields["state"].selection, string="OC A")
    po_last_note          = fields.Char("OC Nota")
    po_log_count          = fields.Integer("OC #Cambios")


# --------------------------
# WIZARD (transient)
# --------------------------
class PrPoAnalyticReportWizard(models.TransientModel):
    _name = "pr.po.analytic.report.wizard"
    _description = "Wizard PR ↔ PO (Distribución Analítica)"

    date_from = fields.Date(string="Desde", required=True, default=lambda self: date(date.today().year, date.today().month, 1))
    date_to = fields.Date(string="Hasta", required=True, default=fields.Date.today)
    company_ids = fields.Many2many("res.company", string="Compañías", default=lambda self: self.env.company)
    only_with_po = fields.Boolean(string="Solo con Orden de Compra")
    line_ids = fields.One2many("pr.po.analytic.report.line", "wizard_id", string="Resultados", readonly=True)

    def _build_sql_and_params(self):
        """SQL basada en tu consulta, parametrizada y con IDs para M2O clicables,
        incluyendo trazabilidad (último estado y conteo) para PR y OC."""
        self.ensure_one()
        sql = r"""
            SELECT
                -- IDs para M2O
                pr.company_id                               AS company_id,
                pr.id                                       AS request_id,
                po.id                                       AS po_id,
                rp.id                                       AS provider_id,
                aaa.id                                      AS analytic_account_id,
                rp_aa.id                                    AS analytic_client_id,

                -- Campos visibles
                pr.name                                     AS request_name,
                pr.state                                    AS request_state,

                pt.default_code                             AS product_code,
                COALESCE(pt.name->>'es_EC', pt.name->>'en_US', pt.name->>'es_ES') AS product_name,
                prl.product_qty                             AS req_qty,

                po.name                                     AS po_number,
                po.state                                    AS po_state,

                REPLACE(REPLACE(rp.name, E'\n',' '), E'\r','')     AS proveedor,
                pol.product_qty                             AS po_qty,
                pol.price_unit                              AS po_price_unit,
                pol.price_subtotal                          AS po_price_subtotal,

                aaa.name                                    AS analytic_account,
                dist.percent_num                            AS analytic_percent,
                REPLACE(REPLACE(rp_aa.name, E'\n',' '), E'\r','')  AS analytic_client,

                -- Trazabilidad PR (último log y conteo)
                prlog.pr_last_changed_on,
                prlog.pr_last_changed_by_id,
                prlog.pr_last_state_from,
                prlog.pr_last_state_to,
                prlog.pr_last_note,
                prstat.pr_log_count,

                -- Trazabilidad PO (último log y conteo)
                polog.po_last_changed_on,
                polog.po_last_changed_by_id,
                polog.po_last_state_from,
                polog.po_last_state_to,
                polog.po_last_note,
                postat.po_log_count

            FROM purchase_request pr
            JOIN purchase_request_line prl
              ON prl.request_id = pr.id
            LEFT JOIN uom_uom uom
              ON uom.id = prl.product_uom_id
            LEFT JOIN product_product pp
              ON pp.id = prl.product_id
            LEFT JOIN product_template pt
              ON pt.id = pp.product_tmpl_id

            -- Enlace requisición ↔ orden de compra
            LEFT JOIN purchase_request_purchase_order_line_rel rel
              ON rel.purchase_request_line_id = prl.id
            LEFT JOIN purchase_order_line pol
              ON pol.id = rel.purchase_order_line_id
            LEFT JOIN purchase_order po
              ON po.id = pol.order_id
            LEFT JOIN res_partner rp
              ON rp.id = po.partner_id

            -- Explode del JSONB analytic_distribution
            LEFT JOIN LATERAL (
                SELECT (kv.key)::int AS analytic_id,
                       (kv.value)::numeric AS percent_num
                FROM jsonb_each_text(pol.analytic_distribution) kv(key, value)
            ) dist
              ON TRUE
            LEFT JOIN account_analytic_account aaa
              ON aaa.id = dist.analytic_id

            -- Cliente (partner) de la cuenta analítica
            LEFT JOIN res_partner rp_aa
              ON rp_aa.id = aaa.partner_id

            -- >>> Trazabilidad PR (último log)
            LEFT JOIN LATERAL (
                SELECT
                    l.changed_on  AS pr_last_changed_on,
                    l.changed_by  AS pr_last_changed_by_id,
                    l.state_from  AS pr_last_state_from,
                    l.state_to    AS pr_last_state_to,
                    l.note        AS pr_last_note
                FROM purchase_request_state_log l
                WHERE l.request_id = pr.id
                ORDER BY l.changed_on DESC, l.id DESC
                LIMIT 1
            ) prlog ON TRUE

            -- Conteo de logs PR
            LEFT JOIN LATERAL (
                SELECT COUNT(*)::int AS pr_log_count
                FROM purchase_request_state_log l
                WHERE l.request_id = pr.id
            ) prstat ON TRUE

            -- >>> Trazabilidad PO (último log)
            LEFT JOIN LATERAL (
                SELECT
                    l.changed_on  AS po_last_changed_on,
                    l.changed_by  AS po_last_changed_by_id,
                    l.state_from  AS po_last_state_from,
                    l.state_to    AS po_last_state_to,
                    l.note        AS po_last_note
                FROM purchase_order_state_log l
                WHERE l.order_id = po.id
                ORDER BY l.changed_on DESC, l.id DESC
                LIMIT 1
            ) polog ON TRUE

            -- Conteo de logs PO
            LEFT JOIN LATERAL (
                SELECT COUNT(*)::int AS po_log_count
                FROM purchase_order_state_log l
                WHERE l.order_id = po.id
            ) postat ON TRUE

            WHERE pr.date_start BETWEEN %s AND %s
        """
        params = [self.date_from, self.date_to]

        if self.company_ids:
            sql += " AND pr.company_id IN %s"
            params.append(tuple(self.company_ids.ids))

        if self.only_with_po:
            sql += " AND po.id IS NOT NULL"

        sql += " ORDER BY pr.id, prl.id, po.id, pol.id, aaa.id"
        return sql, params

    def action_run(self):
        self.ensure_one()
        # limpiar resultados previos del mismo wizard
        self.line_ids.unlink()

        sql, params = self._build_sql_and_params()
        self.env.cr.execute(sql, params)
        rows = self.env.cr.dictfetchall()

        # Preparar create masivo
        to_create = []
        for r in rows:
            to_create.append({
                "wizard_id": self.id,
                "company_id": r.get("company_id"),
                "request_id": r.get("request_id"),
                "request_state": r.get("request_state"),
                "product_code": r.get("product_code"),
                "product_name": r.get("product_name"),
                "req_qty": r.get("req_qty"),

                "po_id": r.get("po_id"),
                "po_state": r.get("po_state"),
                "proveedor_id": r.get("provider_id"),
                "po_qty": r.get("po_qty"),
                "po_price_unit": r.get("po_price_unit"),
                "po_price_subtotal": r.get("po_price_subtotal"),

                "analytic_account_id": r.get("analytic_account_id"),
                "analytic_percent": r.get("analytic_percent"),
                "analytic_client_id": r.get("analytic_client_id"),

                # PR trace
                "pr_last_changed_on": r.get("pr_last_changed_on"),
                "pr_last_changed_by_id": r.get("pr_last_changed_by_id"),
                "pr_last_state_from": r.get("pr_last_state_from"),
                "pr_last_state_to": r.get("pr_last_state_to"),
                "pr_last_note": r.get("pr_last_note"),
                "pr_log_count": r.get("pr_log_count"),

                # PO trace
                "po_last_changed_on": r.get("po_last_changed_on"),
                "po_last_changed_by_id": r.get("po_last_changed_by_id"),
                "po_last_state_from": r.get("po_last_state_from"),
                "po_last_state_to": r.get("po_last_state_to"),
                "po_last_note": r.get("po_last_note"),
                "po_log_count": r.get("po_log_count"),
            })

        if to_create:
            self.env["pr.po.analytic.report.line"].create(to_create)

        # Abrir lista completa (tree) con búsqueda/agrupadores
        return {
            "type": "ir.actions.act_window",
            "name": _("PR ↔ PO (Distribución Analítica)"),
            "res_model": "pr.po.analytic.report.line",
            "view_mode": "tree,search",
            "domain": [("wizard_id", "=", self.id)],
            "target": "current",
        }
