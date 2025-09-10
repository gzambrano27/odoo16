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

class DocumentBankWizard(models.Model):
    _name = "document.bank.wizard"
    _description = "Asistente de Operacion Financiera"

    @api.model
    def _get_default_bank_id(self):
        return self._context.get("active_ids") and self._context.get("active_ids")[0] or False


    document_bank_id=fields.Many2one("document.bank","Documento",ondelete="cascade",default=_get_default_bank_id)

    internal_type = fields.Selection(related="document_bank_id.internal_type",store=False,readonly=True)

    company_id=fields.Many2one(related="document_bank_id.company_id",store=False,readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)
    partner_id = fields.Many2one(related="document_bank_id.partner_id", store=False, readonly=True)

    type_action=fields.Selection([('import','Importado'),   ('process','Procesar')],string="Tipo de Accion",
                                 default="import")

    type=fields.Selection([('compute','Calculado'),
                           ('file','Archivo')],string="Tipo",default="file")

    message=fields.Text("Comentarios")
    amount=fields.Monetary("Valor Nominal",default=0.01)
    percentage_amortize=fields.Float("% por Amortizar",default=0.00,digits=(4,2),compute="compute_capital")
    percentage_type=fields.Selection([('fixed','Fijo')],string="Tipo de % de Interes",default="fixed")
    percentage_interest=fields.Float("% de Interes",default=2.25,digits=(4,2))
    percentage_interest_quota=fields.Float("% de Interes Cuota",default=0.00,digits=(4,6))
    capital = fields.Monetary("Pago de  Capital",default=0.00,compute="compute_capital")
    periods = fields.Integer("# Periodos", default=0, compute="compute_capital")
    years=fields.Integer("Años",default=5)

    file = fields.Binary("Archivo", required=False, filters='*.xlsx')
    file_name = fields.Char("Nombre de Archivo", required=False, size=255)

    line_ids=fields.Many2many("document.bank.line","document_bank_wizard_line_rel","wizard_id","bank_line_id","Detalles")

    payment_amount=fields.Monetary("Monto de Pago",required=True,default=0.01)
    payment_date = fields.Date("Fecha de Pago", required=True, default=fields.Date.today())

    invoice_ids = fields.Many2many("account.move", "document_bank_wizard_invoice_rel", "wizard_id", "invoice_id",
                                "Facturas")


    @api.onchange('percentage_interest','years','periods')
    def  onchange_percentage_interest(self):
        percentage_interest_quota = 0.00
        if self.periods>0:
            percentage_interest_quota=round(self.percentage_interest / float(self.periods), 6)  # cuota abajo
        self.percentage_interest_quota=percentage_interest_quota

    @api.onchange('line_ids')
    def onchange_line_ids(self):
        DEC=2
        payment_amount = sum(line.total_pending for line in self.line_ids)
        self.payment_amount=round(payment_amount,DEC)


    @api.onchange('amount','years')
    def compute_capital(self):
        DEC=2
        for brw_each in self:
            capital=0.00
            periods=0
            percentage_amortize=0.00
            if brw_each.type == "compute":
                if brw_each.years>0:
                    periods=(brw_each.years*12)/3
                    capital=round(brw_each.amount/periods,DEC)
                    if periods>0:
                        percentage_amortize=round(100.00/float(periods),2)
            brw_each.capital=capital
            brw_each.periods=periods
            brw_each.percentage_amortize=percentage_amortize

    @api.constrains('amount')
    def validate_amount(self):
        for brw_each in self:
            if brw_each.type=="compute" and brw_each.type_action=="import":
                if brw_each.amount<=0.00:
                    raise ValidationError(_("El Valor Nominal debe ser mayor a 0"))

    @api.constrains('percentage_amortize')
    def validate_percentage_amortize(self):
        for brw_each in self:
            if brw_each.type == "compute" and brw_each.type_action=="import":
                if brw_each.percentage_amortize <= 0.00:
                    raise ValidationError(_("El % por Amortizar debe ser mayor a 0"))

    @api.constrains('percentage_interest')
    def validate_percentage_interest(self):
        for brw_each in self:
            if brw_each.type == "compute" and brw_each.type_action=="import":
                if brw_each.percentage_interest <= 0.00:
                    raise ValidationError(_("El % de Interes debe ser mayor a 0"))

    @api.constrains('percentage_interest_quota')
    def validate_percentage_interest_quota(self):
        for brw_each in self:
            if brw_each.type == "compute" and brw_each.type_action=="import":
                if brw_each.percentage_interest_quota <= 0.00:
                    raise ValidationError(_("El % de Interes de Cuota debe ser mayor a 0"))

    @api.constrains('years')
    def validate_years(self):
        for brw_each in self:
            if brw_each.type == "compute" and brw_each.type_action=="import":
                if brw_each.years <= 0.00:
                    raise ValidationError(_("El % de Interes debe ser mayor a 0"))



    def process(self):
        for brw_each in self:
            if brw_each.type!="file":
                brw_each.process_compute()
            else:#
                brw_each.process_file()
        return True

    def process_in(self):
        for brw_each in self:
            if brw_each.type!="file":
                raise ValidationError(_("Operacion no implementada"))
            else:#
                brw_each.process_file_in()
        return True

    def process_compute(self):
        DEC=2
        for brw_each in self:
            brw_each.validate_amount()
            brw_each.validate_percentage_amortize()
            brw_each.validate_percentage_interest()
            brw_each.validate_years()
            percentage_interest_quota=brw_each.percentage_interest_quota
            if brw_each.periods:
                percentage_amortize = brw_each.percentage_amortize###acumular hacia arriba
            date_start=brw_each.document_bank_id.date_process
            date_maturity=date_start
            percentage_amortize_acum=0.00
            line_ids=[(5,)]
            for quota in range(1,brw_each.periods+1):
                date_process=date_start + relativedelta(months=quota*3)
                percentage_interest = (brw_each.percentage_interest - (percentage_interest_quota*(quota-1.00)))
                if quota == brw_each.periods:
                    percentage_amortize = 100.00 - percentage_amortize_acum
                else:
                     percentage_amortize_acum+=percentage_amortize

                date_maturity = date_start
                vals={
                    "quota":quota,
                    "date_process":date_process,
                    "percentage_amortize":percentage_amortize,
                    "percentage_interest":percentage_interest,
                    "payment_capital":round(brw_each.amount*percentage_amortize/100.00,DEC),
                    "payment_interest": round((brw_each.amount * percentage_interest/ 100.00), DEC),
                }
                line_ids.append((0,0,vals))
            brw_each.document_bank_id.write({"line_ids":line_ids,"date_maturity":date_maturity,
                                            "amount":brw_each.amount,
                                             "percentage_amortize": brw_each.percentage_amortize,
                                             "percentage_interest": brw_each.percentage_interest,
                                             "percentage_interest_quota": brw_each.percentage_interest_quota,
                                             "capital": brw_each.capital,
                                             "periods": brw_each.periods,
                                             "years": brw_each.years,
                                             "type_document":brw_each.type
                                             })
        return True

    def process_file_in(self):
        DEC=2
        DATE,QUOTA,TOTAL=0,1,2
        for brw_each in self:
            line_ids = [(5,)]
            ext = flObj.get_ext(brw_each.file_name)
            fileName = flObj.create(ext)
            flObj.write(fileName, flObj.decode64(brw_each.file))
            book = open_workbook(fileName)
            sheet = book.sheet_by_name("IMPORTAR")
            quota = 1
            date_maturity = brw_each.document_bank_id.date_process
            total_capital=0.00
            for row_index in range(0, sheet.nrows):
                quota= int(sheet.cell(row_index, QUOTA).value)
                amount = float(str(sheet.cell(row_index, TOTAL).value))
                str_date = str(sheet.cell(row_index, DATE).value)
                date_process = dtObj.parse(str_date,date_format="%Y/%m/%d")
                vals = {
                    "quota": quota,
                    "date_process": date_process,
                    "amount": round(amount, DEC),
                }
                line_ids.append((0, 0, vals))
                date_maturity=date_process
                quota += 1
            periods = quota
            brw_each.document_bank_id.write({"line_ids": line_ids,
                                             "date_maturity": date_maturity,
                                             "amount": total_capital,
                                             "periods": periods,
                                             })
        return True

    def process_file(self):
        DEC=2
        DATE,AMORTIZE_AMOUNT,AMOUNT_INTEREST,CAPITAL,INTEREST,TOTAL=0,1,2,3,4,5
        for brw_each in self:
            line_ids = [(5,)]
            ext = flObj.get_ext(brw_each.file_name)
            fileName = flObj.create(ext)
            flObj.write(fileName, flObj.decode64(brw_each.file))
            book = open_workbook(fileName)
            sheet = book.sheet_by_name("IMPORTAR")
            quota = 1
            date_maturity = brw_each.document_bank_id.date_process
            global_percentage_amortize=0.00
            total_capital=0.00
            for row_index in range(0, sheet.nrows):
                percentage_amortize= float(str(sheet.cell(row_index, AMORTIZE_AMOUNT).value))
                percentage_interest = float(str(sheet.cell(row_index, AMOUNT_INTEREST).value))
                capital = float(str(sheet.cell(row_index,CAPITAL ).value))
                total_capital+= capital
                interest = float(str(sheet.cell(row_index, INTEREST).value))
                str_date = str(sheet.cell(row_index, DATE).value)
                date_process = dtObj.parse(str_date,date_format="%Y/%m/%d")
                if row_index==0:
                    global_percentage_amortize=percentage_amortize
                vals = {
                    "quota": quota,
                    "date_process": date_process,
                    "percentage_amortize": percentage_amortize,
                    "percentage_interest": percentage_interest,
                    "payment_capital": round(capital, DEC),
                    "payment_interest": round(interest, DEC),
                }
                line_ids.append((0, 0, vals))
                date_maturity=date_process
                quota += 1
            periods = quota
            brw_each.document_bank_id.write({"line_ids": line_ids, "date_maturity": date_maturity,
                                             "amount": total_capital,
                                             "percentage_amortize": global_percentage_amortize,
                                             "percentage_interest": brw_each.percentage_interest,
                                             "percentage_interest_quota": brw_each.percentage_interest_quota,
                                             "capital": total_capital,
                                             "periods": periods,
                                             "years":periods/4,
                                             "type_document": brw_each.type
                                             })
        return True

    def process_payment(self):
        DEC = 2
        for brw_each in self:
            if not brw_each.line_ids:
                raise ValidationError(_("Debes definir al menos una linea"))
            payment_amount = sum(line.total_pending for line in brw_each.line_ids)
            if round(brw_each.payment_amount,DEC) > round(payment_amount,DEC):
                brw_each.payment_amount = round(payment_amount,DEC)
                raise ValidationError(_("La cantidad a pagar no puede ser mayor a lo pendiente"))
            if round(brw_each.payment_amount, DEC)<0.00:
                raise ValidationError(_("La cantidad a pagar debe ser mayor a 0.00"))
            if payment_amount == 0:
                raise ValidationError("The total pending amount is zero, no distribution possible.")

            remaining_amount = self.payment_amount

            for line in brw_each.line_ids:
                if remaining_amount <= 0:
                    break  # Si ya no queda cantidad por aplicar, salimos

                # Determinamos cuánto podemos aplicar a la línea según su saldo pendiente
                amount_to_apply = min(line.total_pending, remaining_amount)

                # Reducimos la cantidad pendiente de la línea
                self.env["document.bank.line.payment"].create({
                    "line_id":line.id,
                    "company_id": line.document_id.company_id.id,
                    "date_process":brw_each.payment_date,
                    "amount":amount_to_apply,
                })

                # Restamos lo aplicado de la cantidad total a distribuir
                remaining_amount -= amount_to_apply

            # Si después de distribuir no se ha cubierto toda la cantidad, mostramos un error
            if round(remaining_amount,DEC) < 0:
                raise ValidationError(f"Could not apply the full amount. {remaining_amount} remains.")
        return True

    def process_invoice(self):
        DEC = 2
        for brw_each in self:
            if not brw_each.invoice_ids:
                raise ValidationError(_("Debes definir al menos una factura"))
            # Obtener las facturas previas ya aplicadas que están en estado 'posted'
            old_invoices = brw_each.document_bank_id.line_ids.mapped('invoice_ids').mapped('invoice_id').filtered(
                lambda x: x.state == 'posted')
            # Limpiar las facturas previas de las líneas de banco
            for brw_line in brw_each.document_bank_id.line_ids:
                brw_line.write({"invoice_ids": [(5,)]})
            # Combinar las facturas actuales y las antiguas
            invoices = brw_each.invoice_ids + old_invoices
            invoices_vals={brw_invoice:brw_invoice.amount_total for brw_invoice in invoices}
            # Total disponible en el banco para aplicar
            total = brw_each.document_bank_id.total
            # for brw_line in brw_each.document_bank_id.line_ids:
            #     # Calcular el monto a aplicar, el cual será el mínimo entre el total de la línea y lo restante de la factura
            #     amount_to_apply = brw_line.total
            #     for invoice in invoices:
            #         if amount_to_apply <= 0:
            #             continue  # Si no hay monto para aplicar, seguimos con la siguiente línea
            #         invoice_amount_to_apply=invoices_vals.get(invoice,0.00)
            #         if invoice_amount_to_apply<=0.00:
            #             del invoices_vals[invoice]
            #         # Crear el registro de la aplicación de la factura
            #         self.env["document.bank.line.invoiced"].create({
            #                 "line_id": brw_line.id,
            #                 "company_id": brw_line.document_id.company_id.id,
            #                 "amount": amount_to_apply,
            #                 "invoice_id": invoice.id,
            #             })
            #
            #     # Restar lo aplicado del monto restante de la factura
            #     remaining_amount -= amount_to_apply
            #     # Restar lo aplicado del saldo total
            #     total -= amount_to_apply
            #
            #     # Si ya no queda saldo por aplicar, rompemos el ciclo
            #     if total <= 0:
            #         break
            return True