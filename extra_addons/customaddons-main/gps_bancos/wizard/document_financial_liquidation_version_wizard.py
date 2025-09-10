# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from xlrd import open_workbook
from odoo.exceptions import ValidationError
from ...calendar_days.tools import CalendarManager,DateManager
from ...message_dialog.tools import FileManager
dtObj=DateManager()
clObj=CalendarManager()
flObj=FileManager()

from dateutil.relativedelta import relativedelta

class DocumentFinancialLiquidationVersionWizard(models.Model):
    _name = "document.financial.liquidation.version.wizard"

    _description = "Asistente de Version para Liquidacion"

    @api.model
    def _get_default_document_id(self):
        if self._context.get("active_model","")=="document.financial":
            active_ids = self._context.get('active_ids', [])
            return active_ids and active_ids[0] or False
        if self._context.get("active_model","")=="document.financial.liquidation":
            active_ids = self._context.get('active_ids', [])
            brw_liq=self.env["document.financial.liquidation"].browse(active_ids)
            return brw_liq.document_id.id
        return False

    @api.model
    def document_liquidation_id(self):
        if self._context.get("active_model", "") == "document.financial.liquidation":
            active_ids = self._context.get('active_ids', [])
            return active_ids and active_ids[0] or False
        return False


    document_id = fields.Many2one(
        "document.financial",
        string="Documento Financiero", on_delete="cascade",default=_get_default_document_id
    )

    document_liquidation_id = fields.Many2one(
        "document.financial.liquidation",
        string="Liq. Documento Financiero", on_delete="cascade", default=document_liquidation_id
    )

    company_id = fields.Many2one(related="document_id.company_id", store=False, readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)

    file = fields.Binary("Archivo", required=False, filters='*.xlsx')
    file_name = fields.Char("Nombre de Archivo", required=False, size=255)

    def process_file(self):
        DEC = 2
        NUMBER_LIQUIDATION,QUOTA ,INTEREST_RATE, PAYMENT_INTEREST, PAYMENT_CAPITAL,   TOTAL,SALDO_AMORTIZAR,COLOCADO = 0, 1, 2, 3, 4, 5,6,7
        for brw_each in self:

            ext = flObj.get_ext(brw_each.file_name)
            fileName = flObj.create(ext)
            flObj.write(fileName, flObj.decode64(brw_each.file))
            book = open_workbook(fileName)
            sheet = book.sheet_by_index(0)

            for row_index in range(1, sheet.nrows):
                number_liquidation = (str(sheet.cell(row_index, NUMBER_LIQUIDATION).value).replace(',', ''))
                quota = int(sheet.cell(row_index, QUOTA).value)
                principal_amount = float(str(sheet.cell(row_index, PAYMENT_CAPITAL).value).replace(',', ''))
                interest_amount = float(str(sheet.cell(row_index, PAYMENT_INTEREST).value).replace(',', ''))

                interest_rate = float(str(sheet.cell(row_index, INTEREST_RATE).value).replace(',', ''))
                total = float(str(sheet.cell(row_index, TOTAL).value).replace(',', ''))

                saldo_amortizar = float(str(sheet.cell(row_index,SALDO_AMORTIZAR ).value).replace(',', ''))
                monto_colocado = float(str(sheet.cell(row_index, COLOCADO).value).replace(',', ''))

                domain=[
                            ('document_id','=',brw_each.document_id.id),
                            ('liquidation_id.number_liquidation','=',number_liquidation),
                            ('document_line_id.quota', '=', quota),
                ]
                if brw_each.document_liquidation_id:
                    domain+= [
                        ('liquidation_id', '=', brw_each.document_liquidation_id.id)
                ]
                srch_placement=self.env["document.financial.placement"].sudo().search(domain)
                if not srch_placement:
                    raise ValidationError(_("No existe colocacion para cuota %s del documento %s,# de liquidacion %s") % (quota,brw_each.document_id.name,number_liquidation))

                vals = {
                    "principal_amount": round(principal_amount, DEC),
                    "interest_amount": round(interest_amount, DEC),
                    "interest_rate": round(interest_rate, DEC),
                    "total": round(total, DEC),
                    "remaining_balance": round(saldo_amortizar, DEC),
                    "placed_amount": round(monto_colocado, DEC),
                }

                srch_placement.write(vals)
            #brw_each.document_financial_id.write({"liquidation_ids": liquidation_ids     })
        return True


