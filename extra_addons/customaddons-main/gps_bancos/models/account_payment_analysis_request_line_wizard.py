from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime,date
from dateutil.relativedelta import relativedelta

from ...calendar_days.tools import DateManager,CalendarManager
from ...message_dialog.tools import FileManager
dtObj=DateManager()
calendarO=CalendarManager()
fileO=FileManager()
from datetime import datetime, timedelta
import re
from .import DEFAULT_MODE_PAYMENTS

class AccountPaymentAnalysisRequestLineWizard(models.Model):
    _name = 'account.payment.analysis.request.line.wizard'
    _description = "Detalle de Asistente de Analisis de Pagos"

    counter = fields.Integer("# C.", help="# Cuentas", default=0,compute="_compute_analize_accounts",store=True,readonly=True)

    request_wizard_id=fields.Many2one('account.payment.analysis.request.wizard','Solicitud',ondelete="cascade")
    invoice_line_id=fields.Many2one('account.move.line','Linea Contable',required=True)
    invoice_id = fields.Many2one(related="invoice_line_id.move_id",store=False,readonly=True,string="Asiento")
    company_id = fields.Many2one(related="invoice_id.company_id", store=False, readonly=True, string="Empresas")
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True, string="Moneda")

    date_maturity = fields.Date(related="invoice_line_id.date_maturity",store=False,readonly=True,string="Fecha de Venc.")
    account_id = fields.Many2one(related="invoice_line_id.account_id",store=False,readonly=True,string="Cuenta")
    partner_id = fields.Many2one(related="invoice_line_id.partner_id", store=False, readonly=True, string="Proveedor")
    name = fields.Char(related="invoice_line_id.name", store=False, readonly=True, string="Etiqueta")
    debit = fields.Monetary(related="invoice_line_id.debit", store=False, readonly=True, string="Débito")
    credit = fields.Monetary(related="invoice_line_id.credit", store=False, readonly=True, string="Crédito")
    amount = fields.Monetary("Saldo",required=True)
    #amount_residual=fields.Monetary(related="invoice_line_id.amount_residual", store=False, readonly=True, string="Saldo Actual")
    comments=fields.Html('Observación',compute="_compute_analize_accounts",store=True,readonly=True)

    amount_residual = fields.Monetary(string="Saldo Actual", readonly=True, compute="_compute_amount_residual")

    default_mode_payment = fields.Selection(DEFAULT_MODE_PAYMENTS, string="Forma de Pago",
                                            default="bank")

    @api.depends('invoice_line_id.amount_residual')
    def _compute_amount_residual(self):
        for rec in self:
            rec.amount_residual = abs(rec.invoice_line_id.amount_residual or 0.0)

    @api.onchange('amount', 'amount_residual')
    def _onchange_amount_validate(self):
        for rec in self:
            if rec.amount and rec.amount_residual and rec.amount > rec.amount_residual:
                rec.amount = rec.amount_residual
                return {
                    'warning': {
                        'title': "Advertencia",
                        'message': "El monto no puede ser mayor al saldo actual.",
                    }
                }

    @api.depends('default_mode_payment')
    @api.onchange('default_mode_payment')
    def _compute_analize_accounts(self):
        for brw_line in self:
            counter = 0
            comments = []
            if brw_line.default_mode_payment == 'bank':
                if not brw_line.partner_id.bank_ids:
                    comments.append('<p style="color:red;">Proveedor no tiene cuenta</p>')
                for brw_partner_bank in brw_line.partner_id.bank_ids:
                    if not brw_partner_bank.acc_number:
                        comments.append('<p style="color:red;"># de Cuenta Vacío</p>')
                    if len(brw_partner_bank.acc_number) == 9:
                        comments.append('<p style="color:orange;"># de Cuenta normalmente tiene 9 dígitos</p>')
                    if not re.fullmatch(r'[0-9]+', brw_partner_bank.acc_number) or re.fullmatch(r'0+',
                                                                                                brw_partner_bank.acc_number):
                        comments.append(
                            '<p style="color:red;">La cuenta %s debe contener solo números y no ser todo ceros.</p>' % brw_partner_bank.acc_number)

                    if brw_partner_bank.acc_number and ' ' in brw_partner_bank.acc_number:
                        comments.append(
                            '<p style="color:red;">El número de cuenta %s NO debe contener espacios en blanco.</p>' % brw_partner_bank.acc_number)

                    if not brw_partner_bank.tercero:
                        if (not brw_line.partner_id.vat or len(
                                brw_line.partner_id.vat) != 10) and brw_line.partner_id.l10n_latam_identification_type_id == self.env.ref(
                            "l10n_ec.ec_dni"):
                            comments.append(
                                '<p style="color:red;"># de Cédula %s debería tener 10 dígitos</p>' % brw_line.partner_id.vat)
                        if (not brw_line.partner_id.vat or len(
                                brw_line.partner_id.vat) != 13) and brw_line.partner_id.l10n_latam_identification_type_id == self.env.ref(
                            "l10n_ec.ec_ruc"):
                            comments.append(
                                '<p style="color:red;"># de RUC %s debería tener 13 dígitos</p>' % brw_line.partner_id.vat)
                    else:
                        if (not brw_partner_bank.identificacion_tercero or len(
                                brw_partner_bank.identificacion_tercero) != 10) and brw_partner_bank.l10n_latam_identification_tercero_id == self.env.ref(
                            "l10n_ec.ec_dni"):
                            comments.append(
                                '<p style="color:red;"># de Cédula de tercero %s debería tener 10 dígitos</p>' % brw_partner_bank.identificacion_tercero)
                        if (not brw_partner_bank.identificacion_tercero or len(
                                brw_partner_bank.identificacion_tercero) != 13) and brw_partner_bank.l10n_latam_identification_tercero_id == self.env.ref(
                            "l10n_ec.ec_ruc"):
                            comments.append(
                                '<p style="color:red;"># de RUC de tercero %s debería tener 13 dígitos</p>' % brw_partner_bank.identificacion_tercero)

                    for brw_bank in self.env["res.bank"].sudo().search([('use_macro_format', '=', True)]):
                        codigos_bancos = brw_bank.get_all_codes()
                        if not codigos_bancos:
                            comments.append(
                                '<p style="color:red;">No hay códigos de bancos recuperados para %s</p>' % brw_bank.name)
                        bic = codigos_bancos.get(brw_partner_bank.bank_id.id, False)
                        if not bic:
                            comments.append('<p style="color:red;">No hay código encontrado para %s para %s</p>' % (
                                brw_bank.name, brw_partner_bank.bank_id.name))

            if brw_line.invoice_id and brw_line.invoice_id.move_type == 'in_invoice':
                withhold_ids = self.env['account.move.line'].search([
                    ('l10n_ec_withhold_invoice_id', '=', brw_line.invoice_id.id),
                    ('move_id.state', '=', 'posted')
                ]).mapped('move_id')
                if not withhold_ids:
                    comments.append('<p style="color:orange;">Factura no tiene retenciones</p>')

                counter += 1

            brw_line.comments = "".join(comments)  # ya es HTML, no uses \n.join()
            brw_line.counter = counter


