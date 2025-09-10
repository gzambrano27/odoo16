# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
import csv
import logging
from datetime import datetime
import re
import unicodedata
from unicodedata import normalize
import hashlib
import tempfile
import csv
import time
import os
import zipfile
import pytz
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)

class AccountRegisterLinePayment(models.TransientModel):
    _name = 'account.payment.line.file'
    _description = 'Account Line Register Payment'

    payment_id = fields.Many2one('account.payment.report', string='Payments')
    partner_id = fields.Many2one('res.partner', string='Partners')

    payment_name = fields.Char(string='Nombre')
    currency = fields.Char(string='Moneda')
    journal_bank_number = fields.Char(string='Cuenta banco empresa')
    type = fields.Char(default='PA')
    payment_method = fields.Char(default='CTA')
    amount = fields.Float('Amount Payment', digits=(6, 2))
    partner_bank_acc_type = fields.Char(string='Tipo cuenta')
    partner_bank_number = fields.Char(string='Cuenta bancaria')
    partner_ci_type = fields.Char(string='Tipo Identificación')
    partner_ci = fields.Char(string='Identificación')
    partner_name = fields.Char(string='Nombre')
    partner_mail = fields.Char(string='Correo')
    circular = fields.Char(string='Circular')
    gloss = fields.Char(string='Glosa')
    bank_code = fields.Char(string='Código Banco')
    bank_name = fields.Char(string='Nombre Banco')
    cajas = fields.Integer('Cajas')
    descuento = fields.Float(string='Descuento', digits=(6, 2))
    ruc_empresa = fields.Char(string='Ruc')
    tipo_cta = fields.Char(string='Tipo Cta')
    semana_embarque = fields.Char(string='Semana Embarque')
    semana_pago = fields.Char(string='Semana Pago')
    plan = fields.Char(string='Plan')
    cod_hacienda = fields.Char(string='Código Hacienda')
    nombre_pago = fields.Char(string='Nombre Pago')
    direccion = fields.Char(string='Dirección')
    precio_oficial = fields.Float('Precio Oficial', digits=(6, 2))
    fecha_embarque = fields.Char(string='Fecha Embarque')
    varios = fields.Char(string='Varios')
    id_pago = fields.Integer('IdBD Pago')

class WizardPaymentReport(models.TransientModel):
    _name = 'account.payment.report'
    _description = 'Download CSV with payment info'
    
    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company)
    banco = fields.Selection([
        ('pichincha', 'Pichincha'),
        ('central', 'Central'),
        #('pacifico', 'Pacifico'),
        ('bolivariano', 'Bolivariano'),
        ('internacional', 'Internacional')
    ], 'Banco', copy=False, default='bolivariano')
    payment_ids = fields.One2many('account.payment.line.file', 'payment_id', readonly=True, string='Payments')
    es_productor = fields.Boolean(string='Archivo para productor?', help="Marcar solo para productores")
    agrupar_cta = fields.Boolean(string='Agrupar x cuenta?', help="Puede Agrupar por cuenta")
    attachment_id = fields.Many2one('ir.attachment', string='Attachment', readonly=True)
    csv_export_file = fields.Binary('CSV File')
    csv_export_filename = fields.Char('CSV Filename', size=50, readonly=True)

    spi_zip_file = fields.Binary('SPI ZIP File', readonly=True)
    spi_zip_filename = fields.Char('SPI ZIP Filename', size=50, readonly=True)
    spi_txt_file = fields.Binary('SPI TXT File', readonly=True)
    spi_txt_filename = fields.Char('SPI TXT Filename', size=50, readonly=True)
    spi_txt_lb_file = fields.Binary('SPI TXT LB File', readonly=True)
    spi_txt_lb_filename = fields.Char('SPI TXT LB Filename', size=50, readonly=True)

    

    # @api.onchange('banco')
    # def onchange_banco(self):
    #     self.update({'payment_ids': []})
    #     if self.payment_ids:
    #         self.payment_ids.unlink()
    #     tabla_datos = self.datos_pagos_banco()
    #     self.update({'payment_ids': tabla_datos})

    @api.onchange('banco')
    def onchange_banco(self):
        # Solo actualiza payment_ids sin afectar el valor de banco
        self.payment_ids = [(5, 0, 0)]  # Borra las líneas actuales
        tabla_datos = self.datos_pagos_banco()
        self.payment_ids = tabla_datos

    @api.model
    def datos_pagos_banco(self):
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        id_wizard = self.id
        
        self.env['account.payment.report'].browse(id_wizard).write({'payment_ids': []})

        if not active_model or not active_ids:
            raise UserError(_('Programmation error: wizard action executed without active_model or active_ids in context.'))
        if active_model != 'account.payment':
            raise UserError(_('Programmation error: the expected model for this action is "account.payment". The provided one is "%s".') % active_model)

        payments = self.env[active_model].browse(active_ids)
        if not payments:
            raise UserError(_('No se encontraron pagos válidos.'))

        if any(payment.state != 'posted' for payment in payments):
            raise UserError(_('Solo pagos validados'))

        if any(payment.payment_method_id.name == 'Check' for payment in payments):
            raise UserError(_('No se permiten cheques'))

        jour = self._get_journal_ids()
        #self._validate_journal(payments, jour)

        reg_lines = self._prepare_reg_lines(payments)
        self.env['account.payment.report'].browse(id_wizard).write({'payment_ids': reg_lines})
        return reg_lines

    def _get_journal_ids(self):
        company = self.company_id.name
        if company == 'IMPORT GREEN POWER TECHNOLOGY, EQUIPMENT & MACHINERY ITEM S.A':
            if self.banco == 'bolivariano':
                return [66,67]
            else: #'internacional':
                return [68]
        if company == 'GREEN ENERGY CONSTRUCTIONS & INTEGRATION C&I SA':
            if self.banco == 'bolivariano':
                return [48,70]
            else:#'internacional':
                return [71,72]
        if company == 'IMPORT BLUE POWER TECHNOLOGY AND MACHINERY S.A.':
            if self.banco == 'bolivariano':
                return [34]
            else:#'internacional':
                return [6]
        if company == 'BLUE ENERGY CONSTRUCTION AND INTEGRATION S.A':
            if self.banco == 'bolivariano':
                return [34]
            else:#'internacional':
                return [6]
                

    def _validate_journal(self, payments, *args):
        # Aquí puedes implementar la validación con payments y otros argumentos si es necesario
        bank_journal_map = {
            'bolivariano': 'Bolivariano',
            'internacional': 'Internacional',
        }
        
        selected_bank = self.banco
        expected_journal_name = bank_journal_map.get(selected_bank)

        if not expected_journal_name:
            raise UserError(_('No se ha configurado un diario válido para el banco seleccionado.'))

        for payment in payments:
            if expected_journal_name.lower() not in payment.journal_id.name.lower():
            #if payment.journal_id.name != expected_journal_name:
                raise UserError(_(
                    'El diario de pago "%s" no corresponde al banco seleccionado "%s". Por favor, seleccione un banco y diario de pago correspondientes.'
                ) % (payment.journal_id.name, selected_bank))

    def _prepare_reg_lines(self, payments):
        reg_lines = []
        for p in payments:
            reg_lines.append([0, 0, self._prepare_payment_line(p)])
        return reg_lines

    def _prepare_payment_line(self, payment):
        partner = payment.partner_id
        bank_info = self._get_bank_info(partner)
        return {
            'payment_id': payment.id,
            'payment_name': payment.name,
            'journal_bank_number': payment.journal_id.name.split(' ')[0],
            'currency': payment.currency_id.name,
            'amount': payment.amount,
            'partner_bank_acc_type': bank_info['acc_type'],
            'partner_bank_number': bank_info['number'],
            'circular': payment.ref or '',
            'gloss': '',
            'partner_ci_type': partner.l10n_latam_identification_type_id.name[:1].upper() if partner.l10n_latam_identification_type_id else '',
            'partner_ci': partner.vat,
            'partner_name': partner.name,
            'partner_mail': partner.email or '',
            'bank_code': bank_info['code'],
            'bank_name': bank_info['name'],
            'cajas': 0,
            'descuento': 0,
            'ruc_empresa': '',
            'tipo_cta': bank_info['acc_type_code'],
            'semana_embarque': '',
            'semana_pago': '',
            'plan': '',
            'cod_hacienda': '',
            'nombre_pago': str(payment.name)[-13:],
            'direccion': partner.street or '',
            'id_pago': payment.id,
        }

    def _get_bank_info(self, partner):
        if not partner.bank_ids:
            return {'name': '', 'code': '', 'number': '', 'acc_type': '', 'acc_type_code': ''}
        bank = partner.bank_ids[0]
        acc_type_code = '00' if bank.tipo_cuenta == 'Corriente' else '10'
        return {
            'name': bank.bank_id.name,
            'code': bank.bank_id.bic,
            'number': bank.acc_number,
            'acc_type': 'CTE' if bank.tipo_cuenta == 'Corriente' else 'AHO',
            'acc_type_code': acc_type_code
        }
    
    def export_txt(self):
        try:
            tabla_datos = self.datos_pagos_banco()
            context = dict(self._context or {})
            active_model = context.get('active_model')
            active_ids = context.get('active_ids')
            id_wizard = self.id
            payments = self.env[active_model].browse(active_ids)

            jour = self._get_journal_ids()
            self._validate_journal(payments, jour)

            _logger.info("Datos de pagos obtenidos: %s", tabla_datos)

            csvfile = io.StringIO()
            writer = csv.writer(csvfile, delimiter='\t', quoting=csv.QUOTE_NONE, escapechar='')
            fechahoy = datetime.now()
    
            mes = str(fechahoy.month).zfill(2)
            dia = str(fechahoy.day).zfill(2)
            proceso = str(fechahoy.year)[-2:] + mes + dia
            if self.banco == 'internacional':
                # Se recogen los datos de los pagos (por ejemplo, de todos los payment_ids)
                rows_data = [p.read()[0] for p in self.payment_ids]
                # Se llama a un método que genere un set de archivos SPI a partir de todos los pagos internacionales
                result = self.env['spi.file.generator'].generate_spi_files_batch(rows_data)
                
                # Se abren los archivos generados y se asignan a los nuevos campos (convertidos a base64)
                with open(result['download'], 'rb') as f_zip:
                    self.spi_zip_file = base64.b64encode(f_zip.read())
                self.spi_zip_filename = result['file_name']
                
                with open(result['download_1'], 'rb') as f_txt:
                    self.spi_txt_file = base64.b64encode(f_txt.read())
                self.spi_txt_filename = result['file_name_1']
                
                with open(result['download_2'], 'rb') as f_txt_lb:
                    self.spi_txt_lb_file = base64.b64encode(f_txt_lb.read())
                self.spi_txt_lb_filename = result['file_name_2']

                # Crear tres adjuntos para cada archivo generado
                attachment_obj = self.env['ir.attachment']
                
                # Crear adjunto y URL de descarga para el archivo ZIP
                attachment_zip = attachment_obj.create({
                    'name': result['file_name'],
                    'type': 'binary',
                    'datas': base64.b64encode(open(result['download'], 'rb').read()),
                    'mimetype': 'application/zip',
                    'res_model': 'account.payment.report',
                    'res_id': self.id,
                })
                download_url_zip = f"/web/content/{attachment_zip.id}?download=true"

                # Crear adjunto y URL de descarga para el archivo TXT principal
                attachment_txt = attachment_obj.create({
                    'name': result['file_name_1'],
                    'type': 'binary',
                    'datas': base64.b64encode(open(result['download_1'], 'rb').read()),
                    'mimetype': 'text/plain',
                    'res_model': 'account.payment.report',
                    'res_id': self.id,
                })
                download_url_txt = f"/web/content/{attachment_txt.id}?download=true"

                # Crear adjunto y URL de descarga para el archivo TXT LB
                attachment_txt_lb = attachment_obj.create({
                    'name': result['file_name_2'],
                    'type': 'binary',
                    'datas': base64.b64encode(open(result['download_2'], 'rb').read()),
                    'mimetype': 'text/plain',
                    'res_model': 'account.payment.report',
                    'res_id': self.id,
                })
                download_url_txt_lb = f"/web/content/{attachment_txt_lb.id}?download=true"

                # Guardar los nombres en la vista
                self.write({
                    'spi_zip_filename': result['file_name'],
                    'spi_txt_filename': result['file_name_1'],
                    'spi_txt_lb_filename': result['file_name_2'],
                    'spi_zip_file': attachment_zip.datas,
                    'spi_txt_file': attachment_txt.datas,
                    'spi_txt_lb_file': attachment_txt_lb.datas,
                })
                base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                # Retornar una acción para abrir la vista con las descargas
                return {
                    "type": "ir.actions.act_window",
                    "res_model": "account.payment.report",
                    "view_mode": "form",
                    "res_id": self.id,
                    "target": "new",
                    "context": {
                        "download_urls": [download_url_zip, download_url_txt, download_url_txt_lb]
                    }
                }
            
                
                # Se retorna una acción que abra el wizard en modo formulario para que el usuario pueda hacer clic en los enlaces y descargar cada archivo
                return {
                    "type": "ir.actions.act_window",
                    "res_model": "account.payment.report",
                    "view_mode": "form",
                    "res_id": self.id,
                    "target": "new",
                }
            else:
                # --- Comportamiento actual para otros bancos (CSV, etc.) ---
                nombre_archivo, extension = self._get_file_name_and_extension(proceso)
                if self.agrupar_cta:
                    sql_group = """
                        SELECT tipo_cta, direccion, partner_name, partner_bank_acc_type, payment_method, 
                        currency, tipo_cta, bank_name, journal_bank_number, bank_code, bank_name, partner_ci, type, partner_ci_type, partner_bank_number,
                        (SELECT circular FROM account_payment_line_file WHERE payment_id = %s AND circular IS NOT NULL LIMIT 1) AS circular,
                        (SELECT payment_name FROM account_payment_line_file WHERE payment_id = %s LIMIT 1) AS payment_name,
                        SUM(amount) AS amount
                        FROM account_payment_line_file WHERE payment_id = %s
                        GROUP BY tipo_cta, direccion, partner_name, partner_bank_acc_type, payment_method, 
                        currency, tipo_cta, bank_name, journal_bank_number, bank_code, bank_name, partner_ci, type, partner_ci_type, partner_bank_number
                    """ % (self.id, self.id, self.id)
                    self.env.cr.execute(sql_group)
                    ids = self.env.cr.dictfetchall()
                    for x in ids:
                        self._write_row(writer, x)
                        self.env.cr.execute(sql_group)
                        ids = self.env.cr.dictfetchall()
                        for x in ids:
                            self._write_row(writer, x)
                else:
                    i = 0
                    for p in self.payment_ids:
                        i += 1
                        self._write_row(writer, p.read()[0], i)
                file_content = csvfile.getvalue()
                if not file_content.strip():
                    raise UserError(_("El archivo generado está vacío."))
                file_content_base64 = base64.b64encode(file_content.encode())
                self.csv_export_file = file_content_base64
                self.csv_export_filename = nombre_archivo + extension
                base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                attachment_obj = self.env['ir.attachment']
                file_name = nombre_archivo + extension
                attachment_id = attachment_obj.create({'name': f"{file_name}",
                                                    'type': "binary",
                                                    'datas': file_content_base64,
                                                    'mimetype': 'text/csv',
                                                    'store_fname': file_name})
                self.attachment_id = attachment_id.id
                download_url = '/web/content/' + str(attachment_id.id) + '?download=true'
                return {
                    "type": "ir.actions.act_url",
                    "url": str(base_url) + str(download_url),
                    "target": "new",
                }
        except Exception as e:
            _logger.error("Error en export_txt: %s", e)
            raise UserError(_("Error al exportar el archivo: %s") % e)
        
    def download_zip(self):
        """ Método para descargar el archivo ZIP """
        if not self.spi_zip_file:
            raise UserError("No se ha generado el archivo ZIP.")
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self.id}/spi_zip_file/{self.spi_zip_filename}?download=true",
            "target": "self",
        }

    def download_txt(self):
        """ Método para descargar el archivo TXT Principal """
        if not self.spi_txt_file:
            raise UserError("No se ha generado el archivo TXT Principal.")
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self.id}/spi_txt_file/{self.spi_txt_filename}?download=true",
            "target": "self",
        }

    def download_txt_lb(self):
        """ Método para descargar el archivo TXT LB """
        if not self.spi_txt_lb_file:
            raise UserError("No se ha generado el archivo TXT LB.")
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self.id}/spi_txt_lb_file/{self.spi_txt_lb_filename}?download=true",
            "target": "self",
        }

    def export_txtOld(self):
        try:
            tabla_datos = self.datos_pagos_banco()
            context = dict(self._context or {})
            active_model = context.get('active_model')
            active_ids = context.get('active_ids')
            id_wizard = self.id
            payments = self.env[active_model].browse(active_ids)

            jour = self._get_journal_ids()
            self._validate_journal(payments, jour)

            _logger.info("Datos de pagos obtenidos: %s", tabla_datos)

            csvfile = io.StringIO()
            writer = csv.writer(csvfile, delimiter='\t', quoting=csv.QUOTE_NONE, escapechar='')
            fechahoy = datetime.now()
    
            mes = str(fechahoy.month).zfill(2)
            dia = str(fechahoy.day).zfill(2)
            proceso = str(fechahoy.year)[-2:] + mes + dia
    
            nombre_archivo, extension = self._get_file_name_and_extension(proceso)
            if self.agrupar_cta:
                sql_group = """
                    SELECT tipo_cta, direccion, partner_name, partner_bank_acc_type, payment_method, 
                    currency, tipo_cta, bank_name, journal_bank_number, bank_code, bank_name, partner_ci, type, partner_ci_type, partner_bank_number,
                    (SELECT circular FROM account_payment_line_file WHERE payment_id = %s AND circular IS NOT NULL LIMIT 1) AS circular,
                    (SELECT payment_name FROM account_payment_line_file WHERE payment_id = %s LIMIT 1) AS payment_name,
                    SUM(amount) AS amount
                    FROM account_payment_line_file WHERE payment_id = %s
                    GROUP BY tipo_cta, direccion, partner_name, partner_bank_acc_type, payment_method, 
                    currency, tipo_cta, bank_name, journal_bank_number, bank_code, bank_name, partner_ci, type, partner_ci_type, partner_bank_number
                """ % (self.id, self.id, self.id)
                self.env.cr.execute(sql_group)
                ids = self.env.cr.dictfetchall()
                for x in ids:
                    self._write_row(writer, x)
            else:
                i = 0
                for p in self.payment_ids:
                    i += 1
                    self._write_row(writer, p.read()[0], i)
                    _logger.info("Datos de pago: %s", p.read()[0])
            _logger.info("Exportando archivo: %s", csvfile.getvalue().encode())
            
            file_content = csvfile.getvalue()
            _logger.info("Contenido del archivo: %s", file_content)
            if not file_content.strip():
                raise UserError(_("El archivo generado está vacío. Por favor, revise los datos de entrada."))
            file_content_base64 = base64.b64encode(file_content.encode())
            self.csv_export_file = file_content_base64
            self.csv_export_filename = nombre_archivo + extension


            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            attachment_obj = self.env['ir.attachment']

            file_name = nombre_archivo + extension
            attachment_id = attachment_obj.create({'name': f"{file_name}",
                                                'type': "binary",
                                                'datas': file_content_base64,
                                                'mimetype': 'text/csv',
                                                'store_fname': file_name})
            self.attachment_id = attachment_id.id
            download_url = '/web/content/' + str(attachment_id.id) + '?download=true'
            return {
                "type": "ir.actions.act_url",
                "url": str(base_url) + str(download_url),
                "target": "new",
            }
        except Exception as e:
            _logger.error("Error en export_txt: %s", e)
            raise UserError(_("Error al exportar el archivo: %s") % e)
        

    def _get_file_name_and_extension(self, proceso):
        if self.banco == 'machala':
            if self.es_productor:
                nombre_archivo = 'PB_07709_' + proceso
            else:
                proceso = str(datetime.now().year) + proceso[2:]
                nombre_archivo = 'MACH_' + proceso + '_1540'
            extension = '.txt'
        elif self.banco == 'pacifico':
            nombre_archivo = 'PACIFICO_PROD_' + proceso if self.es_productor else 'PACIFICO_PROV_' + proceso
            extension = '.txt'
        elif self.banco == 'bolivariano':
            nombre_archivo = 'BOLIVARIANO_PROD_' + proceso if self.es_productor else 'GREEN_PROV_' + proceso
            extension = '.BIZ'
        elif self.banco == 'internacional':
            nombre_archivo = 'INTERNACIONAL_PROD_' + proceso if self.es_productor else 'INTERNACIONAL_PROV_' + proceso
            extension = '.txt'
        else:  # pichincha
            nombre_archivo = 'detalle_pagos' + proceso
            extension = '.txt'
        return nombre_archivo, extension
    
    def quitar_tildes(texto):
        # Normalizar el texto a su forma descompuesta
        texto_normalizado = unicodedata.normalize('NFD', texto)
        # Eliminar los caracteres diacríticos (tildes, ñ, etc.)
        texto_sin_tildes = ''.join(
            char for char in texto_normalizado if unicodedata.category(char) != 'Mn'
        )
        return texto_sin_tildes

    def _write_row(self, writer, row_data, i):
        _logger.info("Escribiendo fila: %s", row_data)
        codbanco = '11074'
        company = self.company_id.name
        if company == 'IMPORT GREEN POWER TECHNOLOGY, EQUIPMENT & MACHINERY ITEM S.A':
            codbanco = '11074'  # Verificar!
        if company == 'GREEN ENERGY CONSTRUCTIONS & INTEGRATION C&I SA':
            codbanco = '11100'  # Verificar!
        if self.banco == 'bolivariano':
            tipo_cta = '03' if row_data['partner_bank_acc_type'] == 'CTE' else '04'
            #code_bank = 'CUE001'.ljust(8) if row_data['bank_code'] == '37' else 'COB001'.ljust(8)
            forma_pago = 'CUE' if row_data['bank_code'] == '37' else 'COB'
            code_bank = '34' if row_data['bank_code'] == '37' else row_data['bank_code'] 
            pname = re.sub(r'[^0-9]', '', row_data['payment_name'].replace('.', ''))
            codpago = re.sub(r'[^0-9]', '', pname)
            idpago = row_data['id_pago']
            fila = (
                    'BZDET' + str(i).zfill(6) +  # 001-011
                    row_data['partner_ci'][:18].ljust(18) +  # 012-029
                    row_data['partner_ci_type'].ljust(1) +  # 030-030
                    row_data['partner_ci'][:14].ljust(14) +  # 031-044
                    row_data['partner_name'][:60].ljust(60) +  # 045-104
                    forma_pago[:3] +  # 105-107
                    '001' +  # Código de país (001) 108-110
                    #code_bank[:2].ljust(2) +  # 111-112
                    ' ' * 2+ # 111-112
                    tipo_cta +  # 113-114
                    row_data['partner_bank_number'][:20].ljust(20) +  # 115-134
                    '1' +  # Código de moneda (1) 135-135
                    str("{:.2f}".format(row_data['amount'])).replace('.', '').zfill(15) +  # 136-150
                    row_data['circular'][:60].ljust(60) +  # 151-210
                    #(row_data['payment_name']).zfill(14) +  # 211-225
                    str(idpago).zfill(15) +  # 211-225
                    '0' * 15 +  # Número de comprobante de retención 226-240
                    '0' * 15 +  # Número de comprobante de IVA 241-255
                    '0' * 20 +  # Número de factura - SRI 256-275
                    ' ' * 9 +  # Código de grupo 276-285
                    ' ' * 50 +  # Descripción del grupo 286-335
                    row_data['direccion'][:50].ljust(50) +  # Dirección del beneficiario 336-385
                    ' ' * 21 +  # Teléfono 386-405
                    'PRO' +  # Código del servicio 406-408
                    ' ' * 10 * 3 +  # Cédula 1, 2, 3 para retiro 409-438
                    ' ' +  # Seña de control de horario 439-439
                    codbanco +  # Código empresa asignado 440-444
                    '0' +  # Código de sub-empresa 445-450
                    codbanco +  # Código de sub-empresa 445-450
                    'RPA' + #code_bank[:2].ljust(2) +  # Sub-motivo de pago/cobro 451-453
                    ' ' * 10 + 
                    code_bank[:2].ljust(2)
                    )
            writer.writerow([fila])
        if self.banco == 'internacionalx':
            tipo_cta = 'CTE' if row_data['partner_bank_acc_type'] == 'CTE' else 'AHO'
            #code_bank = 'CUE001'.ljust(8) if row_data['bank_code'] == '37' else 'COB001'.ljust(8)
            forma_pago = 'CUE' if row_data['bank_code'] == '37' else 'COB'
            code_bank = '34' if row_data['bank_code'] == '37' else row_data['bank_code'] 
            pname = re.sub(r'[^0-9]', '', row_data['payment_name'].replace('.', ''))
            codpago = re.sub(r'[^0-9]', '', pname)
            
            fila = [
                'PA',
                row_data['partner_ci'],
                'USD',
                str("{:.2f}".format(row_data['amount'])).replace('.', ''),
                'CTA',
                tipo_cta,
                row_data['partner_bank_number'],
                row_data['payment_name'],
                row_data['partner_ci_type'],
                row_data['partner_ci'],
                row_data['partner_name'],
                row_data['bank_code']
            ]
            writer.writerow(fila)
        if self.banco == 'internacional':
            self.env['spi.file.generator'].generate_spi_files(row_data, i, self.banco)
    
        
class SPIFileGenerator(models.Model):
    _name = 'spi.file.generator'

    def generate_spi_files_batch(self, rows_data):
        # Usamos un código fijo para los nombres de archivos
        code_fixed = "00001"
        
        # Inicialización de variables para acumular datos
        global_line = []
        total = 0.0
        check = 0
        count = 0
        spi_lb = {}  # Para agrupar beneficiarios si es necesario

        # Se obtiene la cuenta SPI que se utilizará en todos los registros
        bank_spi = self.env['res.partner.bank'].search([('id', '=', 742)], limit=1)
        
        # Recorremos cada pago para generar las líneas de detalle
        for row_data in rows_data:
            count += 1
            # En el detalle podemos usar un número secuencial (o mantener un código fijo para cada línea)
            detail = [str(count).zfill(6)]
            bank_amount_value = int(round(row_data['amount'] * 100))
            bank_amount_str = f"{bank_amount_value:0>6d}"
            detail.append(bank_amount_str)
            total += float(bank_amount_value) / 100.0
            detail.append('40101')
            detail.append(row_data['bank_code'].zfill(8))
            detail.append(row_data['partner_bank_number'].zfill(18))
            account_type = '03' if row_data['partner_bank_acc_type'] == 'CTE' else '04'
            detail.append(account_type)
            beneficiary = row_data['partner_name'].replace(',', ' ').replace(';', ' ').replace('"', '')
            detail.append(self.str2ascii(beneficiary.ljust(30)[:30]))
            voucher = row_data['circular']
            notes_line = f"COMPROBANTE DE PAGO {voucher}".ljust(80)[:80]
            detail.append(notes_line.replace(',', ' ').replace(';', ' ').replace('"', '').replace('\n', '').replace('\r', ''))
            detail.append(row_data['partner_ci'])
            global_line.append(detail)
            check += (int(bank_amount_str) +
                    int(row_data['partner_bank_number']) +
                    int(row_data['bank_code']) +
                    (int('40101') * 5) +
                    (int(bank_spi.acc_number) * 2) + 107)
            
            # Acumular datos para la lista de beneficiarios
            if row_data['partner_ci'] not in spi_lb:
                spi_lb[row_data['partner_ci']] = {
                    'line': [
                        self.str2ascii(beneficiary.ljust(30)[:30]),
                        row_data['partner_bank_number'],
                        row_data['bank_code'],
                        '2'  # Tipo de proveedor
                    ],
                    'amount': float(bank_amount_value) / 100.0
                }
            else:
                spi_lb[row_data['partner_ci']]['amount'] += float(bank_amount_value) / 100.0

        # Fecha en la zona horaria del usuario
        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)
        current_datetime = fields.Datetime.now()
        real_date = pytz.utc.localize(current_datetime).astimezone(local_tz)
        date_02 = real_date.strftime("%d/%m/%Y %H:%M:%S")
        
        # Línea de resumen para el archivo principal
        detail_summary = [date_02, str(count).zfill(10), str(count).zfill(6), '01']
        bank_amount_total_str = f"{int(round(total * 100)):0>21d}"
        detail_summary.append(bank_amount_total_str)
        detail_summary.append(str(check).zfill(22))
        detail_summary.append(bank_spi.acc_number.zfill(8))
        detail_summary.append(bank_spi.acc_number.zfill(8))
        detail_summary.append(self.str2ascii(bank_spi.partner_id.name.ljust(30)[:30]))
        detail_summary.append(bank_spi.bank_id.city.ljust(30)[:30])
        detail_summary.append(time.strftime('%m/%Y'))
        
        # Definir rutas en un directorio temporal usando el código fijo para los nombres
        temp_dir = tempfile.gettempdir()
        file_name = f"SPI-SP_{code_fixed}.txt"
        file_path = os.path.join(temp_dir, file_name)
        file_name_1 = f"SPI-SP-LB_{code_fixed}.txt"
        file_path_1 = os.path.join(temp_dir, file_name_1)
        
        # Escritura de los archivos TXT
        with open(file_path, 'w', newline='') as bank_file, open(file_path_1, 'w', newline='') as bank_file_1:
            csv_file = csv.writer(bank_file, delimiter=',')
            csv_file_1 = csv.writer(bank_file_1, delimiter='\t')
            csv_file.writerow(detail_summary)
            csv_file.writerows(global_line)
            # Escribir archivo de Lista de Beneficiarios (LB)
            csv_file_1.writerow([time.strftime("%d/%m/%Y"), bank_spi.acc_number, self.str2ascii(bank_spi.partner_id.name.ljust(30)[:30])])
            for personal_id, data in spi_lb.items():
                csv_file_1.writerow([personal_id, *data['line'], str(data['amount'])])
        
        # Crear el archivo MD5 para el TXT principal
        md5_hash = self._get_md5_from_file(file_path)
        md5_file_path = file_path.replace('.txt', '.md5')
        with open(md5_file_path, 'w') as md5_file:
            md5_file.write(f"{md5_hash} {file_name}")
        
        # Crear archivo ZIP que contenga el TXT principal y su MD5, usando el nombre fijo
        zip_file_name = f"SPI-SP_{code_fixed}.zip"
        zip_file_path = os.path.join(temp_dir, zip_file_name)
        with zipfile.ZipFile(zip_file_path, 'w') as zip_file_obj:
            zip_file_obj.write(file_path, arcname=file_name)
            zip_file_obj.write(md5_file_path, arcname=os.path.basename(md5_file_path))
        
        return {
            'file_name': zip_file_name,
            'download': zip_file_path,
            'file_name_1': file_name,
            'download_1': file_path,
            'file_name_2': file_name_1,
            'download_2': file_path_1
        }

    @staticmethod
    def str2ascii(string):
        """
        Convert a string to ASCII format, so replace accentuated characters to
        their ASCII equivalent, and delete characters which doesn't have an
        equivalent.

        :param str string: The string to convert to ASCII.
        :return: A copy of string in ASCII.
        """
        try:
            string = unicode(string, 'utf-8')
        except:
            pass
        return normalize('NFKD', string).encode('ascii', 'ignore')

    @staticmethod
    def _get_md5_from_file(file_name):
        """
        Obtiene el hash MD5 del contenido del archivo.

        :param str file_name: Ruta y nombre del archivo.
        :return str: Hash MD5 del contenido del archivo.
        """
        try:
            # Se abre el archivo en modo binario
            with open(file_name, "rb") as file_to_convert:
                md5_hash = hashlib.md5()
                
                # Leer en fragmentos de 4 KB para evitar problemas con archivos grandes
                for chunk in iter(lambda: file_to_convert.read(4096), b""):
                    md5_hash.update(chunk)

            return md5_hash.hexdigest()
        except FileNotFoundError:
            print(f"❌ Error: El archivo '{file_name}' no existe.")
            return None
        except PermissionError:
            print(f"❌ Error: No tienes permisos para leer el archivo '{file_name}'.")
            return None
        except Exception as e:
            print(f"❌ Error desconocido al leer el archivo '{file_name}': {e}")
            return None

    def generate_spi_files(self, row_data, i, banco):
        if banco != 'internacional':
            return {}

        """
        Genera archivos SPI Transfer Banco Central:
        - Archivo TXT con los detalles de transferencia
        - Archivo MD5 para verificación
        - Archivo ZIP con los archivos generados
        """

        # Generar código único para el archivo
        code = str(i).zfill(6)

        # Definir nombres y rutas de archivos
        temp_dir = tempfile.gettempdir()
        file_name = f"SPI-SP_{code.replace('/', '_')}.txt"
        file_path = os.path.join(temp_dir, file_name)

        file_name_1 = f"SPI-SP-LB_{code.replace('/', '_')}.txt"
        file_path_1 = os.path.join(temp_dir, file_name_1)

        # Escritura de archivo principal SPI
        with open(file_path, 'w', newline='') as bank_file, open(file_path_1, 'w', newline='') as bank_file_1:
            csv_file = csv.writer(bank_file, delimiter=',')
            csv_file_1 = csv.writer(bank_file_1, delimiter='\t')

            # Obtener la cuenta bancaria SPI
            res_partner_bank_obj = self.env['res.partner.bank']
            bank_spi = res_partner_bank_obj.search([('id', '=', 742)])

            global_line = []
            spi_lb = {}
            total = 0.0
            check = 0
            count = 0

            # Detalles de la transacción
            detail = [code]
            bank_amount_value = int(round(row_data['amount'] * 100))
            bank_amount_str = f"{bank_amount_value:0>6d}"
            detail.append(bank_amount_str)
            total += float(bank_amount_value) / 100.0

            detail.append('40101')  # Línea de crédito fija
            detail.append(row_data['bank_code'].zfill(8))
            detail.append(row_data['partner_bank_number'].zfill(18))

            account_type = '03' if row_data['partner_bank_acc_type'] == 'CTE' else '04'
            detail.append(account_type)

            beneficiary = row_data['partner_name'].replace(',', ' ').replace(';', ' ').replace('"', '')
            detail.append(self.str2ascii(beneficiary.ljust(30)[:30]))

            voucher = row_data['circular']
            notes_line = f"COMPROBANTE DE PAGO {voucher}".ljust(80)[:80]
            detail.append(notes_line.replace(',', ' ').replace(';', ' ').replace('"', '').replace('\n', '').replace('\r', ''))
            detail.append(row_data['partner_ci'])

            global_line.append(detail)
            count += 1

            # Suma de control
            check += (int(bank_amount_str) +
                      int(row_data['partner_bank_number']) +
                      int(row_data['bank_code']) +
                      (int('40101') * 5) +
                      (int(bank_spi.acc_number) * 2) + 107)

            # Archivo LB (Lista de Beneficiarios)
            if row_data['partner_ci'] not in spi_lb:
                spi_lb[row_data['partner_ci']] = {
                    'line': [
                        self.str2ascii(beneficiary.ljust(30)[:30]),
                        row_data['partner_bank_number'],
                        row_data['bank_code'],
                        '2'  # Tipo de proveedor
                    ],
                    'amount': float(bank_amount_value) / 100.0
                }
            else:
                spi_lb[row_data['partner_ci']]['amount'] += float(bank_amount_value) / 100.0

            # Fecha en zona horaria del usuario
            user_tz = self.env.user.tz or 'UTC'
            local_tz = pytz.timezone(user_tz)
            current_datetime = fields.Datetime.now()
            real_date = pytz.utc.localize(current_datetime).astimezone(local_tz)
            date_02 = real_date.strftime("%d/%m/%Y %H:%M:%S")

            detail = [date_02, code.zfill(10), str(count).zfill(6), '01']
            bank_amount_total_str = f"{int(round(total * 100)):0>21d}"
            detail.append(bank_amount_total_str)
            detail.append(str(check).zfill(22))
            detail.append(bank_spi.acc_number.zfill(8))
            detail.append(bank_spi.acc_number.zfill(8))
            detail.append(self.str2ascii(bank_spi.partner_id.name.ljust(30)[:30]))
            detail.append(bank_spi.bank_id.city.ljust(30)[:30])
            detail.append(time.strftime('%m/%Y'))
            csv_file.writerow(detail)
            csv_file.writerows(global_line)

            # Archivo LB
            csv_file_1.writerow([time.strftime("%d/%m/%Y"), bank_spi.acc_number, self.str2ascii(bank_spi.partner_id.name.ljust(30)[:30])])
            for personal_id, data in spi_lb.items():
                csv_file_1.writerow([personal_id, *data['line'], str(data['amount'])])

        # Crear archivo MD5
        md5_hash = self._get_md5_from_file(file_path)
        md5_file_path = file_path.replace('.txt', '.md5')
        with open(md5_file_path, 'w') as md5_file:
            md5_file.write(f"{md5_hash} {file_name}")

        # Crear archivo ZIP
        zip_file_path = file_path.replace('.txt', '.zip')
        with zipfile.ZipFile(zip_file_path, 'w') as zip_file_obj:
            zip_file_obj.write(file_path, arcname=file_name)
            zip_file_obj.write(md5_file_path, arcname=os.path.basename(md5_file_path))

        return {
            'file_name': file_name.replace('.txt', '.zip'),
            'download': zip_file_path,
            'file_name_1': file_name,
            'download_1': file_path,
            'file_name_2': file_name_1,
            'download_2': file_path_1
        }