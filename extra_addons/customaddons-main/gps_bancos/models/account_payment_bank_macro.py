# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from odoo import fields, models, api, _
from collections import defaultdict
from odoo import fields, _
from odoo.exceptions import ValidationError, UserError

import re
import unicodedata
import base64
import io
import csv
from datetime import datetime

import pytz
from .import DEFAULT_MODE_PAYMENTS

class AccountPaymentBankMacro(models.Model):
    _name = 'account.payment.bank.macro'
    _description = "Pagos con Macros Bancarias"

    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']



    @api.onchange('max_amount_payments')
    def _onchange_max_amount_payments(self):
        if self.max_amount_payments <= 0:
            raise ValidationError("El monto límite debe ser mayor a 0.")

    @api.model
    def _get_default_date_request(self):
        return fields.Date.context_today(self)

    company_id = fields.Many2one("res.company","Compañia",required=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)
    journal_id=fields.Many2one("account.journal","Diario",required=True)
    name=fields.Char("# Proceso",required=True)
    amount=fields.Monetary(string="Pagado",compute="_compute_total",store=True,readonly=True,tracking=False)
    pending = fields.Monetary(string="Pendiente",compute="_compute_total",store=True,readonly=True,tracking=False)
    line_ids = fields.One2many("account.payment.bank.macro.line","bank_macro_id","Lineas de Pagos")
    date_request =fields.Date(string="Fecha de Solicitud",default=_get_default_date_request)
    date_payment = fields.Date(string="Fecha de Pago", default=_get_default_date_request,tracking=True)
    max_amount_payments = fields.Monetary("Monto Límite", required=True,tracking=True)
    dif_max_amount_payments = fields.Monetary(string="Diferencias", compute="_compute_total", store=False,
                                              readonly=True)

    comments = fields.Text("Comentarios",tracking=True)
    state = fields.Selection([('draft', 'Preliminar'),
                              ('generated', 'Generado'),
                              ('confirmed', 'Confirmado'),
                              ('done', 'Realizado'),
                              ('cancelled', 'Anulado'),
                              ], string="Estado", default="draft", tracking=True)

    mode_macro=fields.Selection([('group','Pago Agrupado'),
                                 ('individual','Pago por Transaccion')],tracking=True,default="individual",string="Modo",required=True)

    summary_ids=fields.One2many("account.payment.bank.macro.summary","bank_macro_id","Resumen de Pagos")

    csv_export_file = fields.Binary(string="Archivo Reporte")
    csv_export_filename = fields.Char(stirng="Nombre Archivo")

    enable_value_payments=fields.Boolean(string="Habilitar Campos Edicion",compute="_compute_enable_value_payments",store=False,readonly=True)

    number_invoices = fields.Integer(string="# Facturas", compute="_compute_numbers",
                                           store=False, readonly=True)
    number_orders = fields.Integer(string="# Ordenes", compute="_compute_numbers",
                                     store=False, readonly=True)
    number_payments = fields.Integer(string="# Pagos", compute="_compute_numbers",
                                     store=False, readonly=True)
    number_employee_payments = fields.Integer(string="# Sol. Nominas", compute="_compute_numbers",
                                     store=False, readonly=True)

    number_payslip_payments = fields.Integer(string="# Nominas", compute="_compute_numbers",
                                              store=False, readonly=True)
    number_movement_payments = fields.Integer(string="# Movimientos", compute="_compute_numbers",
                                              store=False, readonly=True)

    number_liquidation_payments = fields.Integer(string="# Liquidaciones", compute="_compute_numbers",
                                              store=False, readonly=True)

    number_requests = fields.Integer(string="# Solicitudes", compute="_compute_numbers",
                                     store=False, readonly=True)

    number_reembolsos = fields.Integer(string="# Reembolsos", compute="_compute_numbers",
                                     store=False, readonly=True)
    number_caja_chicas = fields.Integer(string="# Caja Chicas", compute="_compute_numbers",
                                     store=False, readonly=True)

    number_mail_requests = fields.Integer(string="# Envios", compute="_compute_mail_number_mail_requests",
                                     store=False, readonly=True)

    generate_macro = fields.Boolean("Generar Macro", default=False)
    conf_payment_id = fields.Many2one('account.configuration.payment', 'Configuracion de Pago', required=True)

    attachment_id=fields.Many2one('ir.attachment','Adjunto Macro Generada')

    counter_download=fields.Integer("Conteo Descarga",default=0,tracking=True)
    send_mail_batch=fields.Boolean("Enviado Masivamente",default=False)

    ref=fields.Char("Referencia",tracking=True)

    number_week = fields.Integer(string="Semana del Año", compute="_compute_number_week", store=True)

    type_module = fields.Selection([('financial', 'Financiero'),
                                    ('payslip', 'Nómina')], string="Tipo de Módulo", default="financial")

    default_mode_payment = fields.Selection(DEFAULT_MODE_PAYMENTS, string="Forma de Pago", default="bank",tracking=True)

    macro_bank_type=fields.Selection([('interbancaria','interbancaria'),
                                      ('intrabancaria','intrabancaria')],string="Transferencia",compute="_compute_macro_bank_type",default=None,store=True,required=False)

    @api.depends('default_mode_payment','line_ids','line_ids.bank_account_id')
    @api.onchange('default_mode_payment','line_ids', 'line_ids.bank_account_id')
    def _compute_macro_bank_type(self):
        for rec in self:
            rec.macro_bank_type = None
            if rec.default_mode_payment=='bank':
                if not rec.line_ids or not rec.journal_id.bank_id:
                    continue
                journal_bank = rec.journal_id.bank_id
                all_banks = rec.line_ids.mapped('bank_account_id.bank_id')

                # Si hay algún banco distinto al del diario → interbancaria
                if any(bank != journal_bank for bank in all_banks):
                    rec.macro_bank_type = 'interbancaria'
                # Si todos son del mismo banco → intrabancaria
                elif all_banks:
                    rec.macro_bank_type = 'intrabancaria'

    def get_mode_payment_dscr(self):
        self.ensure_one()
        record=self
        mode_payment_dscr = dict(self._fields['default_mode_payment'].selection).get(
                record.default_mode_payment, '')
        return mode_payment_dscr

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []

        if name:
            domain = ['|', '|',
                      ('ref', operator, name),
                      ('name', operator, name),
                      ('id', '=', name if name.isdigit() else 0)]

        records = self.search(domain + args, limit=limit)
        return records.name_get()

    @api.depends('date_payment')
    def _compute_number_week(self):
        for rec in self:
            if rec.date_payment:
                rec.number_week = rec.date_payment.isocalendar()[1]
            else:
                rec.number_week = False

    def update_lines_ref(self):
        for brw_each in self:
            if not brw_each.ref  is None:
                if brw_each.state=='done':
                    #journal_name = brw_each.journal_id.name.lower()
                    #if 'bolivariano' in journal_name:
                    summary_ids=brw_each.summary_ids
                    if summary_ids:
                        i=1
                        for brw_summary in summary_ids:
                            if brw_summary.ref is None or not brw_summary.ref or brw_summary.ref=="":
                                updated_ref="%s-%s" % (brw_each.ref,i)
                                brw_summary.write({"ref":updated_ref})
                            i+=1


    _order="id desc"

    _rec_name = "name"
    _check_company_auto = True

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        raise ValidationError(_("No puedes duplicar este documento"))

    @api.depends('state', 'line_ids', 'line_ids.payment_id', 'line_ids.request_id' )
    def _compute_numbers(self):
        for brw_each in self:
            # Inicializa los sets para evitar duplicados
            invoices = set()
            orders = set()
            payments = set()
            requests = set()
            employee_payments=set()
            number_payslip_payments=set()
            number_movement_payments = set()
            number_liquidation_payments=set()
            reembolsos = set()
            caja_chicas = set()

            # Itera una sola vez sobre las líneas
            for line in brw_each.line_ids:
                if line.request_id:
                    if line.request_id.invoice_id:
                        invoices.add(line.request_id.invoice_id)
                    if line.request_id.reembolso_id:
                        reembolsos.add(line.request_id.reembolso_id)
                    if line.request_id.caja_chica_id:
                        caja_chicas.add(line.request_id.caja_chica_id   )
                    if line.request_id.order_id:    orders.add(line.request_id.order_id)
                    if line.request_id.payment_employee_id:
                        employee_payments.add(line.request_id.payment_employee_id)
                        # Agrega las líneas de movimiento
                        for movement_line in line.request_id.payment_employee_id.movement_line_ids:
                            number_movement_payments.add(movement_line)
                        # Agrega las líneas de rol de pago
                        for payslip_line in line.request_id.payment_employee_id.payslip_line_ids:
                            number_payslip_payments.add(payslip_line)
                    if line.request_id.liquidation_employee_id:
                        number_liquidation_payments.add(line.request_id.liquidation_employee_id)
                    requests.add(line.request_id)
                if line.payment_id:
                    payments.add(line.payment_id)

            # Asigna los valores calculados
            brw_each.number_invoices = len(invoices)
            brw_each.number_orders = len(orders)
            brw_each.number_payments = len(payments)
            brw_each.number_requests = len(requests)
            brw_each.number_employee_payments=len(employee_payments)
            brw_each.number_payslip_payments=len(number_payslip_payments)
            brw_each.number_movement_payments = len(number_movement_payments)

            brw_each.number_reembolsos = len(reembolsos)
            brw_each.number_caja_chicas = len(caja_chicas)
            brw_each.number_liquidation_payments=len(number_liquidation_payments)

    @api.depends('summary_ids', 'summary_ids.number_mail_requests')
    def _compute_mail_number_mail_requests(self):
        for brw_each in self:
            brw_each.number_mail_requests = sum(brw_each.summary_ids.mapped('number_mail_requests'))


    @api.onchange('state')
    @api.depends('state')
    def _compute_enable_value_payments(self):
        for brw_each in self:
            enable_value_payments=True
            if brw_each.state!='draft':
                enable_value_payments = False
                current_user = self.env.user
                if current_user.has_group('gps_bancos.group_pagar_sol_pagos') or current_user.has_group('gps_bancos.group_admin_sol_pagos'):
                    if brw_each.state == 'generated':
                        enable_value_payments = True
            brw_each.enable_value_payments=enable_value_payments

    @api.onchange('max_amount_payments', 'line_ids', 'line_ids.pending',
                  'line_ids.amount','line_ids.apply')
    @api.depends('max_amount_payments', 'line_ids', 'line_ids.pending',
                 'line_ids.amount','line_ids.apply')
    def _compute_total(self):
        DEC = 2
        for brw_each in self:
            amount, pending, dif_max_amount_payments = 0.00, 0.00, 0.00
            for brw_line in brw_each.line_ids:
                if brw_line.apply:
                    amount += brw_line.amount
                    pending += brw_line.pending
            brw_each.amount = amount
            brw_each.pending = pending
            brw_each.dif_max_amount_payments = round(brw_each.max_amount_payments - amount, DEC)

    @api.onchange('max_amount_payments', 'line_ids', 'line_ids.pending',
                  'line_ids.amount','mode_macro','line_ids.apply')
    def onchange_mode_macro(self):
        self.ensure_one()
        summary_ids=[(5,)]
        if self.line_ids:
            partner_banks={}
            for brw_line in self.line_ids:
                if brw_line.apply:
                    PK=self.mode_macro=="group" and brw_line.bank_account_id or brw_line
                    PK="%s-%s" % ((brw_line.is_prepayment and "1" or "0"),PK)
                    if not partner_banks.get(PK,False):
                        partner_banks[PK]={
                                "amount":0.00,
                                "line_ids":self.env["account.payment.bank.macro.line"],
                                "partner_id":brw_line.partner_id,
                                "bank_account_id":brw_line.bank_account_id,
                                'comments':set()
                        }
                    amount=partner_banks[PK]["amount"]+brw_line.amount
                    partner_banks[PK]["amount"]=amount
                    partner_banks[PK]["line_ids"] = partner_banks[PK]["line_ids"]+brw_line

                    if brw_line.comments and brw_line.comments not in partner_banks[PK]["comments"]:
                        partner_banks[PK]["comments"].add(brw_line.comments)

            for ky in partner_banks:
                comments = ", ".join(partner_banks[ky]["comments"])

                vals={
                    "amount":partner_banks[ky]["amount"],
                    "line_ids":[(6,0,partner_banks[ky]["line_ids"].ids)] ,
                    "partner_id": partner_banks[ky]["partner_id"].id,
                    "bank_account_id": partner_banks[ky]["bank_account_id"].id,

                    "bank_id": partner_banks[ky]["bank_account_id"] and partner_banks[ky]["bank_account_id"].bank_id.id or False,
                    "bank_acc_number": partner_banks[ky]["bank_account_id"].acc_number,
                    "bank_tipo_cuenta": partner_banks[ky]["bank_account_id"].tipo_cuenta,
                    "tercero":False,
                    "comments": comments,
                }
                if partner_banks[ky]["bank_account_id"].tercero:
                    vals.update({
                        "tercero": True,
                        "identificacion_tercero": partner_banks[ky]["bank_account_id"].identificacion_tercero,
                        "nombre_tercero": partner_banks[ky]["bank_account_id"].nombre_tercero,
                        "l10n_latam_identification_tercero_id": partner_banks[ky]["bank_account_id"].l10n_latam_identification_tercero_id and partner_banks[ky]["bank_account_id"].l10n_latam_identification_tercero_id.id or False
                    })
                summary_ids.append((0,0,vals))
        self.summary_ids=summary_ids

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        brw_new = super(AccountPaymentBankMacro, self).create(vals)
        return brw_new

    def write(self, vals):
        value= super(AccountPaymentBankMacro,self).write(vals)
        if "ref" in vals:
            self.update_lines_ref()
        return value

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        raise ValidationError(_("No puedes duplicar este documento"))

    def action_confirmed(self):
        for brw_each in self:
            if brw_each.amount<=0.00:
                raise ValidationError(_("El monto a pagar debe ser mayor a 0.00"))
            brw_each.write({"state":"confirmed"})
            if brw_each.default_mode_payment=='bank':
                for brw_summary in brw_each.summary_ids:
                    acc_number = brw_summary.bank_account_id.acc_number
                    if not re.fullmatch(r'[0-9]+', acc_number) or re.fullmatch(r'0+', acc_number):
                        raise ValidationError(
                            _("La cuenta bancaria asociada para %s debe contener solo números y no ser todo ceros.") % (
                                brw_summary.partner_id.name,))
        return True

    def action_generated(self):
        for brw_each in self:
            if brw_each.amount <= 0.00:
                raise ValidationError(_("El monto a pagar debe ser mayor a 0.00"))
            #brw_each.validate_grouped_accounts()
            brw_each.write({"state":"generated",
                            "attachment_id":False})
        return True

    def action_draft(self):
        for brw_each in self:
            for brw_line in brw_each.line_ids:
                pass
            brw_each.write({"state":"draft"})
        return True

    def quitar_tildes(texto):
        # Normalizar el texto a su forma descompuesta
        texto_normalizado = unicodedata.normalize('NFD', texto)
        # Eliminar los caracteres diacríticos (tildes, ñ, etc.)
        texto_sin_tildes = ''.join(
            char for char in texto_normalizado if unicodedata.category(char) != 'Mn'
        )
        return texto_sin_tildes

    def limpiar_texto(self,texto):
        """
        Limpia el texto:
        - Elimina tildes y convierte ñ/Ñ a n/N
        - Solo deja letras (sin acentos), números y espacios
        - Elimina cualquier carácter especial que pueda dañar un CSV
        """
        # Normalizar texto para eliminar tildes
        texto_normalizado = unicodedata.normalize('NFKD', texto)
        texto_sin_tildes = ''.join([c for c in texto_normalizado if not unicodedata.combining(c)])

        # Reemplazar ñ y Ñ por n y N
        texto_sin_enies = texto_sin_tildes.replace('ñ', 'n').replace('Ñ', 'N')

        # Eliminar todo lo que no sea letras, números o espacios
        texto_limpio = re.sub(r'[^a-zA-Z0-9 ]', '', texto_sin_enies)

        return texto_limpio.strip()

    def generate_file_macro(self):
        self.ensure_one()
        if self.state=='done':
            if self.attachment_id:
                return self.download_file_macro()
        company = self.company_id.name
        if company == 'IMPORT GREEN POWER TECHNOLOGY, EQUIPMENT & MACHINERY ITEM S.A':
            codbanco = '11074'  # Verificar!
        if company == 'GREEN ENERGY CONSTRUCTIONS & INTEGRATION C&I SA':
            codbanco = '11100'  # Verificar!
        csvfile = io.StringIO()
        writer = csv.writer(csvfile, delimiter='\t', quoting=csv.QUOTE_NONE, escapechar='')
        fechahoy = datetime.now()
        i = 1
        file_name = False
        journal_name = self.journal_id.name.lower()
        if 'bolivariano' in journal_name:
            file_name = 'pago_bol_%s.biz' % (self.name,)
        if 'internacional' in journal_name:
            file_name = 'pago_int_%s.txt' % (self.name,)
        if 'pichincha' in journal_name:
            file_name = 'pago_pichincha_%s.txt' % (self.name,)
        if 'produbanco' in journal_name:
            file_name = 'pago_produbanco_%s.txt' % (self.name,)
        if 'pacifico' in journal_name:
            file_name = 'pago_pacifico_%s.txt' % (self.name,)
        for x in self.summary_ids:
            identificacion = x.partner_id.vat
            tipo_identificacion = (x.partner_id.l10n_latam_identification_type_id == self.env.ref(
                "l10n_ec.ec_dni")) and 'C' or 'P'
            ##########################################################################
            if (x.partner_id.l10n_latam_identification_type_id == self.env.ref(
                    "l10n_ec.ec_ruc")):
                tipo_identificacion = 'R'
            ##########################################################################
            nombre_persona_pago = x.partner_id.name
            if x.bank_account_id.tercero:
                identificacion = x.bank_account_id.identificacion_tercero
                tipo_identificacion = (x.bank_account_id.l10n_latam_identification_tercero_id == self.env.ref(
                    "l10n_ec.ec_dni")) and 'C' or 'P'
                if (x.bank_account_id.l10n_latam_identification_tercero_id == self.env.ref(
                        "l10n_ec.ec_ruc")):
                    tipo_identificacion = 'R'
                nombre_persona_pago = x.bank_account_id.nombre_tercero or nombre_persona_pago
            nombre_persona_pago=self.limpiar_texto(nombre_persona_pago)
            #####################################################banco bolivariano#####################################################3
            if 'bolivariano' in journal_name:
                codigos_bancos = self.env.ref("l10n_ec.bank_12").get_all_codes()
                if not codigos_bancos:
                    raise ValidationError(_("No hay codigos de bancos recuperados para BOLIVARIANO"))
                bic = codigos_bancos.get(x.bank_account_id.bank_id.id, False)
                if not bic:
                    raise ValidationError(
                        _("No hay codigo encontrado para BOLIVARIANO para %s") % (x.bank_account_id.bank_id.name,))
                tipo_cta = '04' if x.bank_account_id.tipo_cuenta == 'Ahorro' else '03'
                # forma_pago = 'CUE' if str(x.employee_id.bank_id.bic)== '37' else 'COB'
                # code_bank = '34' if str(x.employee_id.bank_id.bic) == '37' else str(x.employee_id.bank_id.bic)
                # if code_bank=='213':##juventud ecuatoriana progresista
                #    code_bank='06'
                code_bank = bic
                forma_pago = 'CUE' if bic == '34' else 'COB'

                # if code_bank=='429':##daquilema
                #    code_bank='4102'
                # pname = re.sub(r'[^0-9]', '', row_data['payment_name'].replace('.', ''))
                idpago = x.id
                fila = (
                        'BZDET' + str(i).zfill(6) +  # 001-011
                        identificacion.ljust(18) +  # 012-029
                        tipo_identificacion +  # x.employee_id.partner_id.l10n_latam_identification_type_id.name[:1].upper()+# if x.employee_id.partner_id.l10n_latam_identification_type_id else '' +  # 030-030
                        identificacion.ljust(14) +  # 031-044
                        nombre_persona_pago[:60].ljust(60).replace("Ñ", "N").replace("ñ", "n") +  # 045-104
                        forma_pago[:3] +  # 105-107
                        '001' +  # Código de país (001) 108-110
                        # code_bank[:2].ljust(2) +  # 111-112
                        ' ' * 2 +  # 111-112
                        tipo_cta +  # 113-114
                        x.bank_account_id.acc_number[:20].ljust(20) +  # 115-134
                        '1' +  # Código de moneda (1) 135-135
                        str("{:.2f}".format(x.amount)).replace('.', '').zfill(15) +  # 136-150
                        self.limpiar_texto(x.comments)[:60].ljust(60) +  # 151-210
                        # (row_data['payment_name']).zfill(14) +  # 211-225
                        str(idpago).zfill(15) +  # 211-225
                        '0' * 15 +  # Número de comprobante de retención 226-240
                        '0' * 15 +  # Número de comprobante de IVA 241-255
                        '0' * 20 +  # Número de factura - SRI 256-275
                        ' ' * 9 +  # Código de grupo 276-285
                        ' ' * 50 +  # Descripción del grupo 286-335
                        ('NO TIENE').ljust(
                            50) +  # x.employee_id.partner_id.street[:50].ljust(50)  if x.employee_id.partner_id.street else 'NO TIENE'+  # Dirección del beneficiario 336-385
                        ' ' * 21 +  # Teléfono 386-405
                        'RPA' +  # Código del servicio 406-408
                        ' ' * 10 * 3 +  # Cédula 1, 2, 3 para retiro 409-438
                        ' ' +  # Seña de control de horario 439-439
                        codbanco +  # Código empresa asignado 440-444
                        '0' +  # Código de sub-empresa 445-450
                        codbanco +  # Código de sub-empresa 445-450
                        'RPA' +  # code_bank[:2].ljust(2) +  # Sub-motivo de pago/cobro 451-453
                        ' ' * 10 +
                        code_bank[:5].ljust(5)
                )
                print(fila)
                writer.writerow([fila])
                i = i + 1
            #####################################################banco internacional#####################################################3
            if 'internacional' in journal_name:
                codigos_bancos = self.env.ref("l10n_ec.bank_8").get_all_codes()
                if not codigos_bancos:
                    raise ValidationError(_("No hay codigos de bancos recuperados para INTERNACIONAL"))
                tipo_cta = 'AHO' if x.bank_account_id.tipo_cuenta == 'Ahorro' else 'CTE'
                # code_bank = 'CUE001'.ljust(8) if row_data['bank_code'] == '37' else 'COB001'.ljust(8)
                # forma_pago = 'CUE' if str(x.employee_id.bank_id.bic) == '37' else 'COB'
                # code_bank = str(x.employee_id.bank_id.bic)
                bic = codigos_bancos.get(x.bank_account_id.bank_id.id, False)
                if not bic:
                    raise ValidationError(
                        _("No hay codigo encontrado para INTERNACIONAL para %s") % (x.bank_account_id.bank_id.name,))

                forma_pago = 'CUE' if bic == '37' else 'COB'
                code_bank = bic
                payment_name =self.limpiar_texto( x.comments[:60]).ljust(60)
                pname = re.sub(r'[^0-9]', '', payment_name.replace('.', ''))
                codpago = re.sub(r'[^0-9]', '', pname)
                fila = [
                    'PA',
                    identificacion,
                    'USD',
                    str("{:.2f}".format(x.amount)).replace('.', ''),
                    'CTA',
                    tipo_cta,
                    x.bank_account_id.acc_number,
                    payment_name,
                    tipo_identificacion,
                    identificacion,
                    nombre_persona_pago,
                    code_bank
                ]
                writer.writerow(fila)
            #####################################################banco pichincha#####################################################3
            if 'pichincha' in journal_name:
                codigos_bancos = self.env.ref("l10n_ec.bank_2").get_all_codes()
                if not codigos_bancos:
                    raise ValidationError(_("No hay codigos de bancos recuperados para PICHINCHA"))
                tipo_cta = 'AHO' if x.bank_account_id.tipo_cuenta == 'Ahorro' else 'CTE'
                # code_bank = 'CUE001'.ljust(8) if row_data['bank_code'] == '37' else 'COB001'.ljust(8)
                # forma_pago = 'CUE' if str(x.employee_id.bank_id.bic) == '37' else 'COB'
                # code_bank = str(x.employee_id.bank_id.bic)
                bic = codigos_bancos.get(x.bank_account_id.bank_id.id, False)
                if not bic:
                    raise ValidationError(
                        _("No hay codigo encontrado para PICHINCHA para %s") % (x.bank_account_id.bank_id.name,))

                forma_pago = 'CUE' if bic == '37' else 'COB'
                code_bank = bic
                payment_name = self.limpiar_texto(x.comments)[:60].ljust(60)
                pname = re.sub(r'[^0-9]', '', payment_name.replace('.', ''))
                codpago = re.sub(r'[^0-9]', '', pname)
                fila = [
                    'PA',
                    identificacion,
                    'USD',
                    str("{:.2f}".format(x.amount)).replace('.', ''),
                    'CTA',
                    tipo_cta,
                    x.bank_account_id.acc_number,
                    payment_name,
                    tipo_identificacion,
                    identificacion.zfill(11),
                    nombre_persona_pago,
                    code_bank
                ]
                writer.writerow(fila)
            #####################################################banco produbanco#####################################################3
            if 'produbanco' in journal_name:
                codigos_bancos = self.env.ref("l10n_ec.bank_11").get_all_codes()
                if not codigos_bancos:
                    raise ValidationError(_("No hay codigos de bancos recuperados para PRODUBANCO"))
                if not self.journal_id.bank_account_id:
                    raise ValidationError(_("Diario no tiene configurado un # de Cuenta "))
                tipo_cta = 'AHO' if x.bank_account_id.tipo_cuenta == 'Ahorro' else 'CTE'
                # code_bank = 'CUE001'.ljust(8) if row_data['bank_code'] == '37' else 'COB001'.ljust(8)
                # forma_pago = 'CUE' if str(x.employee_id.bank_id.bic) == '37' else 'COB'
                # code_bank = str(x.employee_id.bank_id.bic)
                bic = codigos_bancos.get(x.bank_account_id.bank_id.id, False)
                if not bic:
                    raise ValidationError(
                        _("No hay codigo encontrado para PRODUBANCO para %s") % (
                            x.bank_account_id.bank_id.name,))

                forma_pago = 'CUE' if bic == '37' else 'COB'
                code_bank = bic
                payment_name = self.limpiar_texto(x.comments)[:200].ljust(200)
                pname = re.sub(r'[^0-9]', '', payment_name.replace('.', ''))
                codpago = re.sub(r'[^0-9]', '', pname)
                   # 045-104
                fila = [
                    'PA',#Código Orientación
                    self.journal_id.bank_account_id.acc_number.zfill(11),##Cuenta Empresa
                    str(i).zfill(7),#Secuencial Pago
                    str(x.id),#Comprobante de Pago
                    identificacion,#Contrapartida
                    'USD',#mONEDA
                    str("{:.2f}".format(x.amount)).replace('.', '').zfill(11),#Valor
                    'CTA',#Forma de Pago
                    code_bank.zfill(4),#Código de Institución Financiera
                    tipo_cta,#Tipo de Cuenta
                    x.bank_account_id.acc_number.zfill(11),#Número d Cuenta
                    tipo_identificacion  ,#Tipo ID Cliente
                    identificacion,#Número ID Cliente Beneficiario
                    nombre_persona_pago[:60].ljust(60).replace("Ñ", "N").replace("ñ", "n"),#Nombre del Cliente
                    '',#Dirección Beneficiario
                    '',#Ciudad Beneficiario
                    '',#Teléfono Beneficiario
                    'GUAYAQUIL',#Localidad de pago
                    payment_name,#Referencia
                    x.bank_account_id.partner_email and 'PAGOS VARIOS| '+x.bank_account_id.partner_email or 'PAGOS VARIOS'#Referencia Adicional
                ]
                writer.writerow(fila)
            #####################################################banco produbanco#####################################################3
            if 'pacifico' in journal_name:
                payment_name = self.limpiar_texto(x.comments)[:20].ljust(20)
                tipo_cta = '10' if x.bank_account_id.tipo_cuenta == 'Ahorro' else '00'
                if self.macro_bank_type=='intrabancaria':
                    # csvfile.write(
                    #     '1OCPPR' + p.tipo_cta + p.partner_bank_number.zfill(8) + str(amount_total).zfill(15).ljust(
                    #         30) + p.nombre_pago.ljust(20) + 'CUUSD' + p.partner_name.encode('utf-8').ljust(
                    #         34) + partner_ci_type + p.partner_ci)
                   fila = (
                            '1' +  # Tipo de registro
                            'OCP'.ljust(3) +  # Código operación
                            'PR'.ljust(2) +  # Producto
                            tipo_cta.ljust(2) +  # Tipo de cuenta (10=ahorro,00=cte)
                            " " * 8 +  # Cuenta destino (8 posiciones)
                            str("{:.2f}".format(x.amount)).replace('.', '').zfill(
                                15) +  # Valor (15 posiciones sin punto decimal)
                            identificacion.ljust(15) +  # Cédula/RUC del beneficiario
                            payment_name.ljust(20) +  # Concepto de pago
                            'CU'.ljust(2) +  # Tipo de documento
                            'USD'.ljust(3) +  # Moneda
                            nombre_persona_pago[:30].ljust(30).replace("Ñ", "N").replace("ñ",
                                                                                         "n") +  # Nombre del beneficiario
                            " " * 2 +#localidad de retiro de cheque
                            " " * 2  +#agencia retiro del cheque
                            tipo_identificacion.ljust(1) +  # Tipo de identificación (C/R/P)
                            identificacion.ljust(14) +  # Número identificación
                            ''.ljust(10)  #telefono del beneficiairo
                    )
                if self.macro_bank_type == 'interbancaria':
                    codigos_bancos = self.env.ref("l10n_ec.bank_7").get_all_codes()
                    if not codigos_bancos:
                        raise ValidationError(_("No hay codigos de bancos recuperados para PACIFICO"))
                    if not self.journal_id.bank_account_id:
                        raise ValidationError(_("Diario no tiene configurado un # de Cuenta "))
                    bic = codigos_bancos.get(x.bank_account_id.bank_id.id, False)
                    if not bic:
                        raise ValidationError(
                            _("No hay codigo encontrado para PACIFICO para %s") % (
                                x.bank_account_id.bank_id.name,))
                    code_bank = bic
                    # csvfile.write('1OCPRU'+p.tipo_cta+'00000000'+str(amount_total).zfill(15)+
                    #               '00000'.ljust(15)+
                    #               'PAGO PACIFICO'.ljust(20)+'CUUSD'+
                    #               p.partner_name.encode('utf-8').ljust(34)+
                    #               (partner_ci_type+p.partner_ci).ljust(76)+bank_code.encode('utf-8')+
                    #               p.partner_bank_number.ljust(20))
                    fila = (
                                '1' +  # Tipo de registro
                                'OCP'.ljust(3) +  # Código operación
                                'RU'.ljust(2) +  # Producto
                                tipo_cta.ljust(2) +  # Tipo de cuenta (10=ahorro,00=cte)
                                '0'.zfill(8) +  # Cuenta destino (8 posiciones)
                                str("{:.2f}".format(x.amount)).replace('.', '').zfill(
                                    15) +  # Valor (15 posiciones sin punto decimal)
                                '00000'.ljust(15)+#?dentificación del Servicio
                                'PAGO PACIFICO'.ljust(20)+#?
                                'CU'.ljust(2) +  # Tipo de documento
                                'USD'.ljust(3) +  # Moneda
                                nombre_persona_pago[:30].ljust(30).replace("Ñ", "N").replace("ñ",
                                                                                             "n") +  # Nombre del beneficiario
                                " " * 2+  # localidad de retiro de cheque
                                " " * 2 + # agencia retiro del cheque
                                tipo_identificacion.ljust(1) +  # Tipo de identificación (C/R/P)
                                identificacion.ljust(14) +  # Número identificación
                                ''.ljust(10) +  # telefono del beneficiairo
                                ' '   +  #Tipo NUC del Ordenante
                                ''.ljust(14)+  # Número único del    Ordenante
                                ''.ljust(30)+  #Nombre del Ordenante del Cheque
                                ''.ljust(6) +  # Secuencial de número de lote
                               code_bank.ljust(2) +  #Código Banco
                                x.bank_account_id.acc_number.ljust(20)  #Número de Cuenta de Otros Bancos
                        )
                writer.writerow([fila])
        file_content = csvfile.getvalue()
        if not file_name:
            raise ValidationError(_("No hay nombre definido para el archivo"))
        if not file_content.strip():
            raise ValidationError(_("El archivo generado está vacío. Por favor, revise los datos de entrada."))
        file_content_base64 = base64.b64encode(file_content.encode())
        self.csv_export_file = file_content_base64
        self.csv_export_filename = file_name  #
        attachment_obj = self.env['ir.attachment']
        attachment_id = attachment_obj.create({'name': f"{file_name}",
                                               'type': "binary",
                                               'datas': file_content_base64,
                                               'mimetype': 'text/csv',
                                               'store_fname': file_name })
        # (opcional) guardar referencia en un campo many2one si existe
        self.attachment_id = attachment_id.id
        self.message_post(
            body='El siguiente adjunto fue generado desde el sistema %s.' % (file_name,)
        )
        return self.download_file_macro()

    def download_file_macro(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].get_param('param.download.bancos.url')
        if not self.attachment_id:
            raise ValidationError(_("No hay adjuntos generados"))
        attachment_id=self.attachment_id
        # Publicar mensaje en el chatter con el adjunto
        ####
        download_url = '/web/content/' + str(attachment_id.id) + '?download=true'
        self.message_post(
            body='Se descargo el archivo macro'
        )
        self.counter_download=self.counter_download+1
        return {
            "type": "ir.actions.act_url",
            "url": str(base_url) + str(download_url),
            "target": "new",
        }


    def validate_grouped_accounts(self):
        """
        Verifica que no existan múltiples cuentas contables diferentes para el mismo partner_id
        si el tipo de solicitud es 'account.move'
        """
        for brw_each in self:
            partner_account_map = {}

            for line in brw_each.line_ids:
                if line.request_id.type == 'account.move':
                    partner_key = line.request_id.partner_id.id
                    account_id = line.payment_account_id.id

                    if partner_key in partner_account_map:
                        if partner_account_map[partner_key] != account_id:
                            raise ValidationError(
                                f"El proveedor '{line.request_id.partner_id.name}' tiene más de una cuenta contable de pago en el asistente."
                            )
                    else:
                        partner_account_map[partner_key] = account_id

    def action_cancel(self):
        for brw_each in self:
            for brw_line in brw_each.line_ids:
                brw_line.write({"apply":False})
                brw_line.onchange_apply()
            brw_each.write({"state":"cancelled"})
        return True

    def action_done(self):
        self.ensure_one()
        brw_each = self
        if brw_each.mode_macro=='individual':
            brw_each.action_done_for_payment()
        else:
            brw_each.action_done_grouped()
        return True

    def action_done_for_payment(self):
        self.ensure_one()
        brw_each=self
        payment_obj=self.env["account.payment"]
        if brw_each.amount <= 0.00:
            raise ValidationError(_("El monto a pagar debe ser mayor a 0.00"))
        for brw_line in self.line_ids:
            if brw_line.apply:
                if brw_line.amount > brw_line.pending:
                    raise ValidationError(_("No puedes pagar mas de lo solicitado %s,%s") % (
                    brw_line.request_id.id, brw_line.request_id.name))
                if brw_line.request_id.state != 'confirmed':
                    raise ValidationError(_("La Solicitud %s,%s debe estar en estado confirmado") % (
                    brw_line.request_id.id, brw_line.request_id.name))
                map_amounts = {}
                if brw_line.request_id.type not in  ('hr.employee.payment',):
                    payment_date=fields.Date.context_today(self)
                    OBJ_PERIOD_LINE = self.env["account.fiscal.year.line"].sudo()
                    brw_period, brw_period_line = OBJ_PERIOD_LINE.get_periods(payment_date, brw_each.company_id,
                                                                              for_account_payment=True)
                    payment_res =  {
                        'payment_type': 'outbound',
                        'partner_id': brw_line.partner_id.id,
                        'partner_type': 'supplier',
                        'journal_id': brw_each.journal_id.id,
                        'company_id': brw_line.request_id.company_id.id,
                        'currency_id': brw_line.request_id.currency_id.id,
                        'date': payment_date,
                        'amount': brw_line.amount,
                        'purchase_id': brw_line.request_id.order_id and brw_line.request_id.order_id.id or False,
                        'payment_method_id': self.env.ref('account.account_payment_method_manual_out').id,
                        'ref': brw_line.comments,
                        "payment_request_id":brw_line.request_id.id,
                        'is_prepayment':brw_line.is_prepayment,
                        "prepayment_account_id":brw_line.prepayment_account_id and brw_line.prepayment_account_id.id or False,
                        'period_id':brw_period.id,
                        'period_line_id': brw_period_line.id,
                        'destination_account_id':brw_line.payment_account_id.id,
                        "name_account":brw_line.bank_account_id.full_name,
                    }
                    payment_purchase_line_ids=[(5,)]
                    if brw_each.type_module != 'payslip':  # es de tipo proveedor
                        if brw_each.company_id.partner_id.id == payment_res['partner_id']:
                            destination_journal_id = self.env["account.journal"].sudo().search([
                                ('company_id', '=', brw_each.company_id.id),
                                ('type', '=', 'bank'),
                                ('bank_account_id', '=', brw_line.bank_account_id.id),
                            ])
                            if not destination_journal_id:
                                raise UserError("No se encontró ningún diario bancario para la cuenta seleccionada.")
                            elif len(destination_journal_id) > 1:
                                raise UserError(
                                    "Se encontraron múltiples diarios bancarios para la cuenta seleccionada. Por favor, revise la configuración.")
                            payment_res["is_internal_transfer"] = True
                            payment_res["destination_journal_id"] = destination_journal_id.id

                    if brw_line.request_id.type == 'purchase.order':
                        payment_purchase_line_ids.append((0, 0, {
                            "order_id": brw_line.request_id.order_id.id,
                            'amount': brw_line.amount
                        }))
                        map_amounts[brw_line.request_id.order_id]=brw_line.amount
                    if brw_line.request_id.type == 'account.move':
                        map_amounts[brw_line.request_id.invoice_id]=brw_line.amount
                    if brw_line.request_id.type == 'hr.employee.liquidation':
                        map_amounts[brw_line.request_id.liquidation_employee_id]=brw_line.amount
                        payment_res["change_payment"] = True
                        payment_line_ids = [(5,), (0, 0, {
                            "account_id": brw_line.payment_account_id.id,
                            "partner_id": brw_line.partner_id.id,
                            "name": brw_line.request_id.liquidation_employee_id.name,
                            "credit": 0.00,
                            "debit": brw_line.amount
                        })]
                        payment_res["payment_line_ids"] = payment_line_ids
                    if brw_line.request_id.type == 'request':
                        if brw_line.request_id.enable_other_account:
                            payment_res["change_payment"] = True
                            payment_line_ids=[(5,)]
                            for brw_payment_request_line in brw_line.request_id.payment_line_ids:
                                payment_line_ids.append((0, 0, {
                                    "account_id": brw_payment_request_line.account_id.id,
                                    "partner_id": brw_payment_request_line.partner_id.id,
                                    "name": brw_payment_request_line.request_id.name,
                                    "credit": brw_line.credit,
                                    "debit": brw_line.debit,
                                    'analytic_id':brw_payment_request_line.request_id.analytic_id and brw_line.request_id.analytic_id.id or False
                                }))
                            payment_res["payment_line_ids"] = payment_line_ids
                            payment_res["is_prepayment"]=False
                            payment_res["prepayment_account_id"] = False
                    payment_res["payment_purchase_line_ids"]=payment_purchase_line_ids
                    #####################################################################################
                    payment = payment_obj.create(payment_res)
                    payment.action_post()
                    brw_line.write({"payment_id":payment.id})
                    payment.update_request_states()
                    if brw_line.type=='purchase.order':
                        if payment.is_prepayment:#si es pago anticipado
                            orders=brw_line.request_id.order_id
                            if orders:
                                invoices = self.get_invoices_from_purchase_orders( orders)  # se extrae facturas
                                #self.reconcile_payment_with_invoice_anticipo(payment, invoices,map_amounts=map_amounts)
                                brw_line.request_id.write({"payment_ids":[(4,payment.id)]})
                        else:
                            orders=brw_line.request_id.order_id
                            if orders:#si hay orden decompra
                                invoices=self.get_invoices_from_purchase_orders(orders)#se extrae facturas
                                self.reconcile_payment_with_invoice(payment, invoices,map_amounts={})#si reconciliar pagos con facturas
                                brw_line.request_id.write({"payment_ids": [(4, payment.id)]})
                    if brw_line.type=='account.move':
                        invoices = brw_line.request_id.invoice_id
                        if invoices:  # si hay orden decompra
                            self.reconcile_payment_with_invoice(payment, invoices,map_amounts=map_amounts)
                            brw_line.request_id.write({"payment_ids": [(4, payment.id)]})
                    if brw_line.type=='hr.employee.liquidation':
                        brw_line.request_id.liquidation_employee_id.action_paid()
                        brw_line.request_id.liquidation_employee_id.write({"payment_id": payment.id})
                        brw_line.request_id.write({"payment_ids": [(4, payment.id)]})
                    if brw_line.type == 'request':
                        brw_line.request_id.write({"payment_ids": [(4, payment.id)]})
                else:####
                    raise ValidationError(_("No esta habilitado esta opcion para pagos individuales"))
                    # if brw_line.request_id.type == 'hr.employee.payment':
                    #     map_amounts[brw_line.request_id.payment_employee_id]=brw_line.amount
                    # brw_payment_employee=brw_line.request_id.payment_employee_id
                    # brw_payment_employee.write({
                    #     "payment_journal_id":brw_each.journal_id.id
                    # })
                    # brw_payment_employee.onchange_payment_journal_id()
                    # brw_payment_employee.onchange_lines()
                    # brw_payment_employee.action_approved()
                    # ###recuperar por lineas
                    # if brw_payment_employee.payslip_line_ids:
                    #     brw_payment=brw_payment_employee.payslip_line_ids.mapped('payment_id')
                    #     brw_line.write({"payment_id":brw_payment.id})
                    #     brw_line.request_id.write({"payment_ids": [(4, brw_payment.id)]})
                    # #######################################
                    # if brw_payment_employee.movement_line_ids:
                    #     brw_payment=brw_payment_employee.movement_line_ids.mapped('payment_id')
                    #     brw_line.write({"payment_id": brw_payment.id})
                    #     brw_line.request_id.write({"payment_ids": [(4, brw_payment.id)]})
        self.write({"state":"done","date_payment":fields.Date.context_today(self)})
        return True

    def action_done_grouped(self):
        self.ensure_one()
        # self.validate_grouped_accounts()
        brw_each = self
        payment_obj = self.env["account.payment"]
        last_payslip_type = None
        is_nomina = False
        all_payslip_types = []
        if brw_each.amount <= 0.00:
            raise ValidationError(_("El monto a pagar debe ser mayor a 0.00"))

        grouped_payments = defaultdict(lambda: {
            'payment_type': 'outbound',
            'partner_id': None,
            'partner_type': 'supplier',
            'journal_id': brw_each.journal_id.id,
            'company_id': None,
            'currency_id': None,
            'date': fields.Date.context_today(self),
            'amount': 0.00,
            'payment_method_id': self.env.ref('account.account_payment_method_manual_out').id,
            'ref': set(),
            'is_prepayment': False,
            'prepayment_account_id': None,
            'period_id': None,
            'period_line_id': None,
            'brw_lines': [],
            'payment_purchase_line_ids': [(5,)],
            'map_amounts': {},
            'map_accounts': {},
            'map_another_accounts': []
        })

        OBJ_PERIOD_LINE = self.env["account.fiscal.year.line"].sudo()
        payment_date = fields.Date.context_today(self)
        brw_period, brw_period_line = OBJ_PERIOD_LINE.get_periods(payment_date, brw_each.company_id,
                                                                  for_account_payment=True)
        pending_rows = 0
        for brw_line in self.line_ids:
            if brw_line.apply:
                if brw_line.payment_id:
                    continue
                pending_rows += 1
                if brw_line.amount > brw_line.pending:
                    raise ValidationError(_("No puedes pagar más de lo solicitado %s, %s") % (
                        brw_line.request_id.id, brw_line.request_id.name))
                if brw_line.request_id.state != 'confirmed':
                    raise ValidationError(_("La Solicitud %s, %s debe estar en estado confirmado") % (
                        brw_line.request_id.id, brw_line.request_id.name))
                partner_id = brw_line.partner_id.id
                name_account = brw_line.bank_account_id.full_name
                if brw_line.request_id.type == 'hr.employee.payment':
                    partner_id = brw_line.request_id.payment_employee_id.get_partner_account_id()
                    name_account = None
                pk_payment_group=brw_line.bank_account_id and brw_line.bank_account_id.id or partner_id
                pk_payment = "%s-%s" % ((brw_line.is_prepayment and "PRE" or "PAY"), pk_payment_group)

                grouped_payments[pk_payment]['partner_id'] = partner_id
                grouped_payments[pk_payment]['name_account'] = name_account
                grouped_payments[pk_payment]['company_id'] = brw_line.request_id.company_id.id
                grouped_payments[pk_payment]['payment_account_id'] = brw_line.payment_account_id.id
                grouped_payments[pk_payment]['currency_id'] = brw_line.request_id.currency_id.id
                grouped_payments[pk_payment]['amount'] += brw_line.amount
                grouped_payments[pk_payment]['is_prepayment'] |= brw_line.is_prepayment
                grouped_payments[pk_payment][
                    'prepayment_account_id'] = brw_line.prepayment_account_id.id if brw_line.prepayment_account_id else None
                grouped_payments[pk_payment]['period_id'] = brw_period.id
                grouped_payments[pk_payment]['period_line_id'] = brw_period_line.id
                grouped_payments[pk_payment]['brw_lines'].append(brw_line)
                payment_purchase_line_ids = grouped_payments[pk_payment]['payment_purchase_line_ids']
                #####################################################################################
                map_amounts = grouped_payments[pk_payment]['map_amounts']
                map_accounts = grouped_payments[pk_payment]['map_accounts']
                if brw_line.request_id.type == 'purchase.order':
                    payment_purchase_line_ids.append((0, 0, {
                        "order_id": brw_line.request_id.order_id.id,
                        'amount': brw_line.amount
                    }))
                    if brw_line.request_id.order_id not in map_amounts:
                        map_amounts[brw_line.request_id.order_id] = 0.00
                    map_amounts[brw_line.request_id.order_id] = map_amounts[
                                                                    brw_line.request_id.order_id] + brw_line.amount
                if brw_line.request_id.type == 'account.move':
                    if brw_line.request_id.invoice_id not in map_amounts:
                        map_amounts[brw_line.request_id.invoice_id] = 0.00
                    map_amounts[brw_line.request_id.invoice_id] = map_amounts[
                                                                      brw_line.request_id.invoice_id] + brw_line.amount
                    if brw_line.payment_account_id not in map_accounts:
                        map_accounts[brw_line.payment_account_id] = 0.00
                    map_accounts[brw_line.payment_account_id] = map_accounts[
                                                                    brw_line.payment_account_id] + brw_line.amount
                if brw_line.request_id.type == 'hr.employee.payment':
                    if last_payslip_type is None:
                        is_nomina = True
                    if brw_line.request_id.payment_employee_id:
                        if last_payslip_type is None:
                            last_payslip_type = brw_line.request_id.payment_employee_id.filter_iess
                        if brw_line.request_id.payment_employee_id.filter_iess != last_payslip_type:
                            raise ValidationError(
                                _("No puedes mezclar documentos de nomina de afiliados y no afiliados"))
                        last_payslip_type = brw_line.request_id.payment_employee_id.filter_iess
                        all_payslip_types = list(
                            set(all_payslip_types + brw_line.request_id.payment_employee_id.get_type_documents()))
                        # last_payslip_type = brw_each.payment_employee_id.filter_iess

                        ####pago fin de mes no afiliado

                        if not last_payslip_type and all_payslip_types[0]=='payslip':  # no afiliado
                            another_accounts = grouped_payments[pk_payment]["map_another_accounts"]
                            if not another_accounts:
                                another_accounts=[(5,)]
                            another_accounts.append((0, 0, {
                                    "account_id": brw_line.payment_account_id.id,
                                    "partner_id": partner_id,
                                    "name":  brw_line.request_id.name,
                                    "credit": 0.00,
                                    "debit": brw_line.amount,
                                    'analytic_id':  False
                            }))
                            grouped_payments[pk_payment]["map_another_accounts"] = another_accounts

                    if brw_line.request_id.payment_employee_id not in map_amounts:
                        map_amounts[brw_line.request_id.payment_employee_id] = 0.00
                    map_amounts[brw_line.request_id.payment_employee_id] = map_amounts[
                                                                               brw_line.request_id.payment_employee_id] + brw_line.amount
                    if brw_line.payment_account_id not in map_accounts:
                        map_accounts[brw_line.payment_account_id] = 0.00
                    map_accounts[brw_line.payment_account_id] = map_accounts[
                                                                    brw_line.payment_account_id] + brw_line.amount
                if brw_line.request_id.type == 'hr.employee.liquidation':
                    all_payslip_types = list(
                        set(all_payslip_types + ["liquidation"]))
                    # if brw_line.request_id.liquidation_employee_id:
                    #     all_payslip_types = list(
                    #         set(all_payslip_types + ["liquidation"]))
                    if brw_line.request_id.liquidation_employee_id not in map_amounts:
                        map_amounts[brw_line.request_id.liquidation_employee_id] = 0.00
                    map_amounts[brw_line.request_id.liquidation_employee_id] = map_amounts[
                                                                                   brw_line.request_id.liquidation_employee_id] + brw_line.amount
                    if brw_line.payment_account_id not in map_accounts:
                        map_accounts[brw_line.payment_account_id] = 0.00
                    map_accounts[brw_line.payment_account_id] = map_accounts[
                                                                    brw_line.payment_account_id] + brw_line.amount

                    if not last_payslip_type and all_payslip_types[0] == 'liquidation':  # no afiliado
                        another_accounts = grouped_payments[pk_payment]["map_another_accounts"]
                        if not another_accounts:
                            another_accounts = [(5,)]
                        another_accounts.append((0, 0, {
                            "account_id": brw_line.payment_account_id.id,
                            "partner_id": partner_id,
                            "name": brw_line.request_id.name,
                            "credit": 0.00,
                            "debit": brw_line.amount,
                            'analytic_id': False
                        }))
                        grouped_payments[pk_payment]["map_another_accounts"] = another_accounts

                if brw_line.request_id.type == 'request':
                    if brw_line.request_id.enable_other_account:
                        brw_payment_account_id=brw_line.payment_account_id
                        if not brw_line.payment_account_id:
                            brw_payment_account_id=brw_line.request_id.payment_line_ids.mapped('account_id')
                        if brw_line.payment_account_id not in map_accounts:
                            map_accounts[brw_payment_account_id] = 0.00
                        map_accounts[brw_payment_account_id] = map_accounts[  brw_payment_account_id] + brw_line.amount
                        if len(brw_line.request_id.payment_line_ids)>1:
                            ###################################################
                            another_accounts=grouped_payments[pk_payment]["map_another_accounts"]
                            for brw_payment_request_line in brw_line.request_id.payment_line_ids:
                                another_accounts.append((0, 0, {
                                    "account_id": brw_payment_request_line.account_id.id,
                                    "partner_id": brw_payment_request_line.partner_id.id,
                                    "name": brw_payment_request_line.request_id.name,
                                    "credit": brw_payment_request_line.credit,
                                    "debit": brw_payment_request_line.debit,
                                    'analytic_id': brw_payment_request_line.request_id.analytic_id and brw_line.request_id.analytic_id.id or False
                                }))
                            grouped_payments[pk_payment]["map_another_accounts"]=another_accounts
                grouped_payments[pk_payment]['payment_purchase_line_ids'] = payment_purchase_line_ids
                grouped_payments[pk_payment]['map_amounts'] = map_amounts
                grouped_payments[pk_payment]['map_accounts'] = map_accounts
                if brw_line.comments and brw_line.comments not in grouped_payments[pk_payment]["ref"]:
                    grouped_payments[pk_payment]["ref"].add(brw_line.comments)
                if brw_each.type_module != 'payslip':  # es proveedor
                    grouped_payments[pk_payment]['partner_bank_id'] = brw_line.bank_account_id.id
                #####################################################################################

        # if pending_rows <= 0:
        #     self.write({"state": "done",
        #                 "date_payment": fields.Date.context_today(self)})
        #     if self.default_mode_payment!='bank':
        #         self.summary_ids.write({})
        # else:
        #     pass
        if len(all_payslip_types) > 1:
            dct_payslip = {
                "liquidation": "Liquidación de Haberes",  # debe ser unitario
                "payslip": "Rol de Pago",
                "batch": "Lote",
                "batch_automatic": "Lote Automático",
                "discount": "Préstamo"  # debe ser unitario
            }
            tipos = [dct_payslip.get(tp, tp) for tp in all_payslip_types]
            tipos_str = ", ".join(tipos)
            raise ValidationError(_(
                "No puedes mezclar diferentes tipos de documentos de nómina en un pago en lote: %s"
            ) % tipos_str)

        agrupar_pago_nomina = is_nomina #and last_payslip_type
        if ('discount' in all_payslip_types) or ('liquidation' in all_payslip_types) or (brw_each.default_mode_payment!='bank'):
            agrupar_pago_nomina = False
        else:
            if agrupar_pago_nomina:  # es nomina y para afiliados
                brw_conf = brw_each.company_id.get_payment_conf()
                agrupar_pago_nomina = brw_conf.group_by_employee_payment
        if agrupar_pago_nomina:  # es nomina y para afiliados

            # Consolidar grouped_payments en un solo pago global
            total_amount = 0.0
            ref_list = []
            all_brw_lines = []
            consolidated_map_accounts = {}
            consolidated_map_amounts = {}
            consolidated_map_another_accounts=[]
            sample_data = list(grouped_payments.values())[0]  # Tomamos cualquier entrada como base

            consolidated_payment = {
                'payment_type': sample_data['payment_type'],
                'partner_id': self.env.company.partner_id.id,
                'partner_type': 'supplier',
                'journal_id': sample_data['journal_id'],
                'company_id': sample_data['company_id'],
                'currency_id': sample_data['currency_id'],
                'date': sample_data['date'],
                'amount': 0.0,
                'payment_method_id': sample_data['payment_method_id'],
                'ref': [],
                'is_prepayment': False,
                'prepayment_account_id': sample_data['prepayment_account_id'],
                'period_id': sample_data['period_id'],
                'period_line_id': sample_data['period_line_id'],
                'brw_lines': [],
                'payment_purchase_line_ids': [(5,)],
                'map_amounts': {},
                'map_accounts': {},
                'payment_account_id': sample_data['payment_account_id'],
                'name_account': '',
                'map_another_accounts':[]
            }

            for data in grouped_payments.values():
                total_amount += data['amount']
                ref_list.extend(list(data['ref']))
                all_brw_lines += data['brw_lines']

                for acc, amt in data['map_accounts'].items():
                    consolidated_map_accounts[acc] = consolidated_map_accounts.get(acc, 0) + amt

                for emp, amt in data['map_amounts'].items():
                    consolidated_map_amounts[emp] = consolidated_map_amounts.get(emp, 0) + amt

                consolidated_map_another_accounts+=data.get('map_another_accounts', [])
            consolidated_payment['amount'] = total_amount
            consolidated_payment['ref'] = ref_list
            consolidated_payment['brw_lines'] = all_brw_lines
            consolidated_payment['map_accounts'] = consolidated_map_accounts
            consolidated_payment['map_amounts'] = consolidated_map_amounts
            consolidated_payment['map_another_accounts'] = consolidated_map_another_accounts

            # Sobreescribe grouped_payments con un solo item
            grouped_payments = {'CONSOLIDADO': consolidated_payment}

        for payment_data in grouped_payments.values():
            if payment_data['amount'] > 0:
                full_ref = ", ".join(payment_data['ref'])
                ref = full_ref
                if len(full_ref) > 255:
                    ref = full_ref[:255]
                    last_comma = ref.rfind(", ")
                    ref = ref[:last_comma] if last_comma != -1 else ref
                payment_res = {
                    'payment_type': payment_data['payment_type'],
                    'partner_id': payment_data['partner_id'],
                    'partner_type': payment_data['partner_type'],
                    'journal_id': payment_data['journal_id'],
                    'company_id': payment_data['company_id'],
                    'currency_id': payment_data['currency_id'],
                    'name_account': payment_data.get('name_account', ''),
                    'date': payment_data['date'],
                    'amount': payment_data['amount'],
                    'payment_method_id': payment_data['payment_method_id'],
                    'ref': ref,
                    'is_prepayment': payment_data['is_prepayment'],
                    'prepayment_account_id': payment_data['prepayment_account_id'],
                    'period_id': payment_data['period_id'],
                    'period_line_id': payment_data['period_line_id'],
                    'payment_purchase_line_ids': payment_data['payment_purchase_line_ids'],
                    'destination_account_id': payment_data['payment_account_id'],
                }
                has_other_account = any(
                    brw_macro.request_id.enable_other_account
                    for brw_macro in payment_data['brw_lines']
                )
                if brw_each.type_module != 'payslip':  # es de tipo proveedor
                    # payment_res["bank_account_id"]=payment_data.get('partner_bank_id',False) and payment_data['partner_bank_id'].id or False
                    if brw_each.company_id.partner_id.id == payment_data['partner_id']:
                        destination_journal_id = self.env["account.journal"].sudo().search([
                            ('company_id', '=', brw_each.company_id.id),
                            ('type', '=', 'bank'),
                            ('bank_account_id', '=', payment_data["partner_bank_id"]),
                        ])
                        if not destination_journal_id:
                            raise UserError("No se encontró ningún diario bancario para la cuenta seleccionada.")
                        elif len(destination_journal_id) > 1:
                            raise UserError(
                                "Se encontraron múltiples diarios bancarios para la cuenta seleccionada. Por favor, revise la configuración.")
                        payment_res["is_internal_transfer"] = True
                        payment_res["destination_journal_id"] = destination_journal_id.id

                if len(payment_data['map_accounts']) > 1 or brw_each.type_module == 'payslip' or has_other_account:
                    analytic_map = {}
                    if has_other_account:
                        for brw_macro_line in payment_data['brw_lines']:
                            account = brw_macro_line.payment_account_id
                            analytic = brw_macro_line.request_id.analytic_id
                            if account and analytic:
                                analytic_map[account.id] = analytic.id
                    payment_res["change_payment"] = True
                    payment_line_ids = [(5,)]
                    map_another_accounts=payment_data.get('map_another_accounts',[])
                    if not map_another_accounts:#####si esta habilitada otras cuentas
                        for brw_line_account in payment_data['map_accounts']:
                            line_account_partner_id = payment_data['partner_id']
                            if brw_each.type_module == 'payslip':
                                if not (all_payslip_types[0] in ("payslip",) and not last_payslip_type):  # es nomina pero no afiliados
                                    line_account_partner_id = brw_each.company_id.partner_id.id
                                    #anticipos(quincena y fact) se contabilizan en un primer asiento x loq debe ir a la compa;ia
                                    #nomina(afiliados) a compa;ia ,no afiliados (a partner)
                                    #prestm
                            payment_line_ids.append((0, 0, {
                                "account_id": brw_line_account.id,
                                "partner_id": line_account_partner_id,
                                "name": ref,
                                "credit": 0.00,
                                "debit": payment_data['map_accounts'][brw_line_account],
                                'analytic_id': analytic_map.get(brw_line_account.id, False)
                            }))
                    else:
                        payment_line_ids+=map_another_accounts
                    payment_res["payment_line_ids"] = payment_line_ids
                payment = payment_obj.create(payment_res)
                payment.action_post()
                ############3
                map_amounts = payment_data['map_amounts']
                for brw_line in payment_data['brw_lines']:
                    #print(brw_line)
                    request = brw_line.request_id
                    brw_line.write({"payment_id": payment.id})
                    payment.update_request_states()

                    if brw_line.type == 'purchase.order':
                        orders = request.order_id
                        if orders:
                            if payment.is_prepayment:
                                request.write({"payment_ids": [(4, payment.id)]})
                            else:
                                invoices = self.get_invoices_from_purchase_orders(orders)
                                self.reconcile_payment_with_invoice(payment, invoices, map_amounts=map_amounts)
                                request.write({"payment_ids": [(4, payment.id)]})

                    elif brw_line.type == 'account.move':
                        invoices = request.invoice_line_ids.mapped('move_id')
                        for brw_invoice in invoices:
                            self.reconcile_payment_with_invoice(payment, brw_invoice, map_amounts=map_amounts)
                        request.write({"payment_ids": [(4, payment.id)]})

                    elif brw_line.type == 'hr.employee.payment':
                        employee_payment = request.payment_employee_id
                        employee_payment.write({"payment_journal_id": brw_each.journal_id.id})
                        employee_payment.onchange_payment_journal_id()
                        employee_payment.onchange_lines()

                        # Movimiento contable y nómina
                        if employee_payment.movement_line_ids:
                            employee_payment.movement_line_ids.write({"payment_id": payment.id})
                        if employee_payment.payslip_line_ids:
                            employee_payment.payslip_line_ids.write({"payment_id": payment.id})

                        # Conciliación
                        invoice_lines = self.env["account.move.line"]
                        for x in payment.move_id.line_ids.filtered(
                                lambda l: l.debit > 0 and l.amount_residual != 0.00):
                            invoice_lines += x
                            for mov in employee_payment.movement_ids:
                                invoice_lines += mov.move_id.line_ids.filtered(
                                    lambda
                                        y: y.credit > 0 and y.partner_id == x.partner_id and y.account_id == x.account_id and y.amount_residual != 0.00
                                )
                            for slip in employee_payment.payslip_ids:
                                invoice_lines += slip.move_id.line_ids.filtered(
                                    lambda
                                        y: y.credit > 0 and y.partner_id == x.partner_id and y.account_id == x.account_id and y.amount_residual != 0.00
                                )

                        if len(invoice_lines) > 1:
                            invoice_lines.reconcile()

                        # Marcar como pagado
                        employee_payment.payslip_line_ids.write({"state": 'paid'})
                        payslip_runs = employee_payment.payslip_line_ids.mapped('payslip_run_id')
                        if payslip_runs:
                            payslip_runs.test_paid()
                        employee_payment.write({"state": "approved"})
                        request.write({"payment_ids": [(4, payment.id)]})

                    elif brw_line.type == 'hr.employee.liquidation':
                        liquidation = request.liquidation_employee_id
                        liquidation.action_paid()
                        liquidation.write({"payment_id": payment.id})
                        request.write({"payment_ids": [(4, payment.id)]})

                    elif brw_line.type == 'request':
                        request.write({"payment_ids": [(4, payment.id)]})

        self.write({"state": "done",
                    "date_payment": fields.Date.context_today(self)})
        if self.default_mode_payment!='bank':
            self.summary_ids.write({})
        return True

    def action_open_payments(self):
        self.ensure_one()
        payments = self.line_ids.mapped('payment_id')
        payments+= payments.mapped('reversed_payment_id')
        payments+= payments.mapped('reversed_payment_ids')

        payments_ids = payments.ids + [-1, -1]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_account_payments_payable"
        )
        action["domain"] = [('id', 'in', payments_ids)]
        return action

    def action_open_purchase_orders(self):
        self.ensure_one()
        purchase_orders=self.line_ids.mapped('request_id').mapped('order_id')
        purchase_orders_ids=purchase_orders.ids+[-1,-1]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "purchase.purchase_form_action"
        )
        action["domain"]=[('id','in',purchase_orders_ids)]
        return action

    def action_open_employee_payments(self):
        self.ensure_one()
        payment_accounts=self.line_ids.mapped('request_id').mapped('payment_employee_id')
        payment_accounts=payment_accounts.ids+[-1,-1]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "gps_hr.hr_employee_payment_view_action"
        )
        action["domain"]=[('id','in',payment_accounts)]
        return action

    def action_open_invoices(self):
        self.ensure_one()
        invoices = self.line_ids.mapped('request_id').mapped('invoice_id')
        invoices_ids = invoices.ids + [-1, -1]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_in_invoice_type"
        )
        action["domain"] = [('id', 'in', invoices_ids)]
        return action

    def action_open_requests(self):
        self.ensure_one()
        requests = self.line_ids.mapped('request_id')
        requests_ids = requests.ids + [-1, -1]
        id_action=(self.type_module=='financial' and
                   "gps_bancos.account_payment_request_view_action" or
                   'gps_bancos.account_payment_request_payslip_view_action')
        action = self.env["ir.actions.actions"]._for_xml_id(
            id_action
        )
        action["domain"] = [('id', 'in', requests_ids)]
        return action

    def action_open_mail_requests(self):
        self.ensure_one()
        summary_ids = self.summary_ids
        summary_ids = summary_ids.ids + [-1, -1]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "gps_bancos.action_bank_mail_message_payslip"
        )
        action["domain"] = [('model_name','=','account.payment.bank.macro.summary'),
                            ('internal_id', 'in', summary_ids)]
        return action

    def show_summary(self):
        self.ensure_one()
        OBJ_MODEL_DATA = self.env["ir.model.data"].sudo()
        tree_id = OBJ_MODEL_DATA.resolve_view_ref("gps_bancos", "account_payment_bank_macro_summary_view_tree_editable")
        context = {}
        v = {
            'name': "Actualizar Referencias de Bancos",
            'view_mode': 'tree',
            'res_model': "account.payment.bank.macro.summary",
            'views': [ (tree_id, 'tree')],
            "context": context,
            'domain': f"[('bank_macro_id','=',{self.id})]",
            'type': 'ir.actions.act_window'
        }
        return v

    @api.model
    def reconcile_payment_with_invoice(self, payment, invoices,map_amounts={}):
        """
        Conciles a payment (account.payment) with an invoice (account.move).

        :param payment: browse record of account.payment
        :param invoice: browse record of account.move
        :return: True if reconciliation is successful
        """
        if not invoices:
            return False
        # Check if the payment is of type supplier
        if payment.payment_type != 'outbound' or payment.partner_type != 'supplier':
            raise UserError(_('El pago proporcionado no es un pago de proveedor.'))

        # for invoice in invoices:
        #     if invoice.move_type != 'in_invoice':
        #         raise UserError(_('El comprobante proporcionado no es una factura de proveedor.'))

        # Ensure the payment and invoice belong to the same supplier
        invoice_amount = 0.00
        for invoice in invoices:
            if (payment.partner_id != invoice.partner_id) and (payment.partner_id not in invoice.line_ids.mapped('partner_id')):
                raise UserError(_('El pago y la factura no pertenecen al mismo proveedor.'))
            invoice_amount += invoice.amount_residual
            # Check the residual amount (remaining amount) of the payment and invoice
            #payment_amount = payment.amount_residual or payment.amount
            payment_amount = payment.amount_residual or payment.amount
            if payment_amount <= 0:
                raise UserError(_('El pago ya ha sido conciliado completamente.'))
            if invoice_amount <= 0:
                return True
            # Create partial reconciliation lines
            invoice_line = invoice.mapped('line_ids').filtered(
                lambda line: line.partner_id==payment.partner_id and  line.account_id.account_type == 'liability_payable' and line.amount_residual != 0.00)
            account_id=     invoice_line and invoice_line.account_id or False
            if account_id:
                payment_line = payment.line_ids.filtered(
                    lambda
                        line: line.account_id==account_id and line.partner_id == payment.partner_id and line.account_id.account_type == 'liability_payable' and line.amount_residual != 0.00)


                if not payment_line or not invoice_line:
                    continue
                    #raise UserError(_('No se encontraron líneas contables adecuadas para conciliar.'))
                brw_reconciles=(payment_line + invoice_line)
                if invoice in map_amounts:
                    brw_reconciles=brw_reconciles.with_context(max_amount=map_amounts[invoice])
                brw_reconciles.reconcile()
            invoice.actualizar_reembolso(payment,map_amounts=map_amounts)
        return True

    @api.model
    def reconcile_payment_with_invoice_anticipo(self, payment, invoices,map_amounts={}):
        """
        Conciles a payment (account.payment) with an invoice (account.move).

        :param payment: browse record of account.payment
        :param invoice: browse record of account.move
        :return: True if reconciliation is successful
        """
        print(payment)
        if not invoices:
            return False
        # Check if the payment is of type supplier
        if payment.payment_type != 'outbound' or payment.partner_type != 'supplier':
            raise UserError(_('El pago proporcionado no es un pago de proveedor.'))

        # Check if the invoice is of type supplier
        for invoice in invoices:
            if invoice.move_type != 'in_invoice':
                raise UserError(_('El comprobante proporcionado no es una factura de proveedor.'))

        # Ensure the payment and invoice belong to the same supplier
        invoice_amount=0.00
        for invoice in invoices:
            if payment.partner_id != invoice.partner_id:
                raise UserError(_('El pago y la factura no pertenecen al mismo proveedor.'))
            invoice_amount+=invoice.amount_residual
        # Check the residual amount (remaining amount) of the payment and invoice
        payment_amount = payment.amount_residual or payment.amount
        if payment_amount <= 0:
            raise UserError(_('El pago ya ha sido conciliado completamente.'))

        if invoice_amount <= 0:
            return True

        # Determine the amount to reconcile


        # Create partial reconciliation lines

        payment_line = payment.move_id.line_ids.filtered(lambda line: line.account_id.account_type == 'asset_prepayments' and line.amount_residual!=0.00)
        if not payment_line:
            return True
        invoice_line = invoices.mapped('line_ids').filtered(lambda line: line.account_id.account_type == 'liability_payable' and line.amount_residual!=0.00)
        if not payment_line or not invoice_line:
            return True
            #raise UserError(_('No se encontraron líneas contables adecuadas para conciliar.'))

        invoices=invoice_line.mapped('move_id')
        for invoice in invoices:
            if invoice.amount_residual!=0.00:
                for each_payment_line in payment_line:
                    payment_amount = payment.amount_residual or payment.amount
                    reconcile_amount = min(payment_amount, invoice.amount_residual)
                    if reconcile_amount>0.00:
                        brw_assignment=self.env["account.prepayment.assignment"].create({
                            "move_id":invoice.id,
                            "prepayment_aml_id":each_payment_line.id,
                            "amount":reconcile_amount,
                            "date":fields.Date.context_today(self),
                            "company_id":invoice.company_id.id,
                            "new_journal_id": payment.journal_id.id
                        })
                        brw_assignment.button_confirm()
        return True

    @api.model
    def get_invoices_from_purchase_orders(self, purchase_orders):
        """
        Retrieves all invoices related to the provided purchase orders.

        :param purchase_orders: Recordset of purchase.order
        :return: Recordset of account.move (invoices)
        """
        if not purchase_orders:
            return self.env['account.move']  # Return an empty recordset
        self._cr.execute("""select am.id ,am.id 
			from purchase_order_line pol
			inner join purchase_order po on po.id=pol.order_id 
			inner join account_move_line aml on aml.purchase_line_id=pol.id
			inner join account_move am on am.id=aml.move_id
			where pol.order_id=%s and am.state='posted' and po.state in ('purchase','done')
			group by am.id """,(purchase_orders.id,))
        result=self._cr.fetchall()
        if result:
            invoice_ids=[*dict(result)]
            # Collect all invoices related to the provided purchase orders
            invoices = self.env['account.move'].sudo().search([
                ('id', 'in', tuple(invoice_ids)),  # Direct link via purchase_id
                ('move_type', 'in', ['in_invoice',]),
                ('state','=','posted'),
                ('partner_id','=',purchase_orders.partner_id.id),# Filter supplier invoices and refunds
                ('amount_residual','!=',0.00)
            ])
            return invoices
        return self.env["account.move"]

    def send_mail(self):
        for brw_each in self:
            if brw_each.state in ("done",):
                if not brw_each.summary_ids:
                    raise ValidationError(_("Al menos un registro debe ser ingresado"))
                for brw_summary in brw_each.summary_ids:
                    if brw_summary.reversed:
                        continue
                    brw_summary=brw_summary.with_context({"internal_type":"batch"})
                    brw_summary.send_mail()
                brw_each.write({"send_mail_batch":True})
        return True

    def get_dsr_states(self):
        self.ensure_one()
        # Obtener las opciones del campo state como una lista de tuplas (valor, etiqueta)
        selection = self._fields['state'].selection

        # Buscar la etiqueta del valor actual
        label = dict(selection).get(self.state, '')

        return label

    ###############
    def action_open_payslips(self):
        self.ensure_one()
        payment_accounts = []
        for line in self.line_ids:
            if line.request_id:
                if line.request_id.payment_employee_id:
                    for payslip_line in line.request_id.payment_employee_id.payslip_line_ids:
                        payment_accounts.append(payslip_line.id)

        payment_accounts=payment_accounts+[-1,-1]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "hr_payroll.action_view_hr_payslip_month_form"
        )
        action["domain"]=[('id','in',payment_accounts)]
        return action

    def action_open_movements(self):
        self.ensure_one()
        payment_accounts=[]
        for line in self.line_ids:
            if line.request_id:
                if line.request_id.payment_employee_id:
                    for movement_line in line.request_id.payment_employee_id.movement_line_ids:
                        payment_accounts.append(movement_line.id)
        payment_accounts=payment_accounts+[-1,-1]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "gps_hr.hr_employee_movement_line_out_view_action"
        )
        action["domain"]=[('id','in',payment_accounts)]
        return action

    def action_open_reembolsos(self):
        self.ensure_one()
        reembolsos=[]
        for line in self.line_ids:
            if line.request_id:
                if line.request_id.reembolso_id:
                     reembolsos.append(line.request_id.reembolso_id.id)
        reembolsos=reembolsos+[-1,-1]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account_payment_purchase.action_registro_reembolso"
        )
        action["domain"]=[('id','in',reembolsos)]
        return action

    def action_open_caja_chicas(self):
        self.ensure_one()
        caja_chicas=[]
        for line in self.line_ids:
            if line.request_id:
                if line.request_id.caja_chica_id:
                     caja_chicas.append(line.request_id.caja_chica_id.id)
        caja_chicas=caja_chicas+[-1,-1]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account_payment_purchase.action_registro_caja_chica"
        )
        action["domain"]=[('id','in',caja_chicas)]
        return action

    def action_open_liquidations(self):
        self.ensure_one()
        payment_accounts = []
        for line in self.line_ids:
            if line.request_id:
                if line.request_id.liquidation_employee_id:
                    payment_accounts.append(line.request_id.liquidation_employee_id.id)
        payment_accounts=payment_accounts+[-1,-1]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "gps_hr.hr_employee_finiquito_view_action"
        )
        action["domain"]=[('id','in',payment_accounts)]
        return action

    def create_intercompany_payment(self):
        print("pago intercompany")

        return True