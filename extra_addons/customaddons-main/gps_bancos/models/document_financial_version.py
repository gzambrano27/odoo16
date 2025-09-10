# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID


class DocumentFinancialVersion(models.Model):
    _name = "document.financial.version"

    _description = "Version"

    @api.model
    def _get_default_name(self):
        active_ids=self._context.get('active_ids',[])
        if active_ids:
            brw_active=self.env["document.financial"].browse(active_ids)
            return brw_active.last_version_id and brw_active.last_version_id.name+1 or 1
        return 1

    @api.model
    def _get_default_document_id(self):
        active_ids = self._context.get('active_ids', [])
        return active_ids and active_ids[0] or False

    @api.model
    def _get_default_line_ids(self):
        active_ids = self._context.get('active_ids', [])
        if active_ids:
            brw_active=self.env["document.financial.version"].browse(active_ids)
            line_ids=[]
            for brw_line in brw_active.line_ids:
                line_ids.append((0,0,{
                   "quota"  :  brw_line.quota,
                    "date_process":brw_line.date_process,
                    "percentage_amortize":brw_line.percentage_amortize,
                    "percentage_interest": brw_line.percentage_interest,
                    "payment_capital": brw_line.payment_capital,
                    "payment_interest": brw_line.payment_interest,
                    "payment_other": brw_line.payment_other,
                    "amount": brw_line.amount,
                    "parent_line_id":brw_line.id,
                    "is_copy":True,

                }))
            return line_ids
        return [(5,)]

    document_id = fields.Many2one(
        "document.financial",
        string="Documento Financiero", on_delete="cascade",default=_get_default_document_id
    )

    company_id = fields.Many2one(related="document_id.company_id", store=False, readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)


    name=fields.Integer("# Version",required=True,default=_get_default_name)
    date=fields.Date("Fecha",required=True,default=fields.Date.context_today)

    line_ids=fields.One2many('document.financial.line','version_id','Detalle',default=_get_default_line_ids)

    total = fields.Monetary("Total", default=0.00, store=True, compute="_compute_total")
    total_to_paid = fields.Monetary("Por Aplicar", default=0.00, required=False, store=True, compute="_compute_total")
    total_paid = fields.Monetary("Aplicado", default=0.00, required=False, store=True, compute="_compute_total")
    total_pending = fields.Monetary("Pendiente", default=0.00, required=False, store=True, compute="_compute_total")


    @api.onchange('line_ids', 'line_ids.total', 'line_ids.total_to_paid', 'line_ids.total_paid',
                  'line_ids.total_pending')
    @api.depends('line_ids', 'line_ids.total', 'line_ids.total_to_paid', 'line_ids.total_paid',
                 'line_ids.total_pending')
    def _compute_total(self):
        DEC = 2
        for brw_each in self:
            total, total_to_paid, total_paid, total_pending = 0.00, 0.00, 0.00, 0.00
            for brw_line in brw_each.line_ids:
                total += brw_line.total
                total_to_paid += brw_line.total_to_paid
                total_paid += brw_line.total_paid
                total_pending += brw_line.total_pending
            brw_each.total = round(total, DEC)
            brw_each.total_to_paid = round(total_to_paid, DEC)
            brw_each.total_paid = round(total_paid, DEC)
            brw_each.total_pending = round(total_pending, DEC)

    _order="document_id asc,name desc"