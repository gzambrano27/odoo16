# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo import fields, _
from odoo.exceptions import ValidationError, UserError

import re
from .macros_bancarias import macros_bancarias

class internacional(macros_bancarias):

    def get_file_name_macro_local(self, obj):
        file_name = 'pago_int_%s.txt' % (obj.name,)
        return file_name

    def generate_file_macro_local(self,obj, writer, journal_name, brw_company):
        i = 1
        for x in obj.summary_ids:
            identificacion = x.partner_id.vat
            tipo_identificacion = (x.partner_id.l10n_latam_identification_type_id == obj.env.ref(
                "l10n_ec.ec_dni")) and 'C' or 'P'
            ##########################################################################
            if (x.partner_id.l10n_latam_identification_type_id == obj.env.ref(
                    "l10n_ec.ec_ruc")):
                tipo_identificacion = 'R'
            ##########################################################################
            nombre_persona_pago = x.partner_id.name
            if x.bank_account_id.tercero:
                identificacion = x.bank_account_id.identificacion_tercero
                tipo_identificacion = (x.bank_account_id.l10n_latam_identification_tercero_id == obj.env.ref(
                    "l10n_ec.ec_dni")) and 'C' or 'P'
                if (x.bank_account_id.l10n_latam_identification_tercero_id == obj.env.ref(
                        "l10n_ec.ec_ruc")):
                    tipo_identificacion = 'R'
                nombre_persona_pago = x.bank_account_id.nombre_tercero or nombre_persona_pago
            nombre_persona_pago = obj.limpiar_texto(nombre_persona_pago)
            #####################################################banco bolivariano#####################################################3
            if 'internacional' in journal_name:
                codigos_bancos = obj.env.ref("l10n_ec.bank_8").get_all_codes()
                if not codigos_bancos:
                    raise ValidationError(_("No hay codigos de bancos recuperados para INTERNACIONAL"))
                tipo_cta = 'AHO' if x.bank_account_id.tipo_cuenta == 'Ahorro' else 'CTE'
                # code_bank = 'CUE001'.ljust(8) if row_data['bank_code'] == '37' else 'COB001'.ljust(8)
                # forma_pago = 'CUE' if str(x.employee_id.bank_id.bic) == '37' else 'COB'
                # code_bank = str(x.employee_id.bank_id.bic)
                bic = codigos_bancos.get(x.bank_account_id.bank_id.id, False)
                if not bic:
                    raise ValidationError(
                        _("No hay código encontrado para INTERNACIONAL para %s") % (x.bank_account_id.bank_id.name,))

                forma_pago = 'CUE' if bic == '37' else 'COB'
                code_bank = bic
                payment_name = obj.limpiar_texto(x.comments[:60]).ljust(60)
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

    def get_file_name_macro_ext(self, obj):
        file_name = 'pago_exterior_int_%s.txt' % (obj.name,)
        return file_name

    def generate_file_macro_ext(self,obj, writer, journal_name, brw_company):
        i = 1

        def fit_field(value, max_len, fill='right', pad_char=' '):
            """
            Ajusta el campo a la longitud máxima permitida.
            - Trunca si es más largo que max_len
            - Rellena con espacios (por defecto) o ceros
            - fill: 'right' para rellenar a la derecha, 'left' para a la izquierda
            """
            val = str(value or '').strip()
            if len(val) > max_len:
                val = val[:max_len]
            if fill == 'right':
                return val.ljust(max_len, pad_char)
            else:
                return val.rjust(max_len, pad_char)

        for x in obj.summary_ids:
            if 'internacional' in journal_name:

                payment_name = obj.limpiar_texto(x.comments[:60]).ljust(60)
                pname = re.sub(r'[^0-9]', '', payment_name.replace('.', ''))
                #codpago = re.sub(r'[^0-9]', '', pname)

                # fila = [
                #     'PA',
                #     identificacion,
                #     'USD',
                #     str("{:.2f}".format(x.amount)).replace('.', ''),
                #     'CTA',
                #     tipo_cta,
                #     x.bank_account_id.acc_number,
                #     payment_name,
                #     tipo_identificacion,
                #     identificacion,
                #     nombre_persona_pago,
                #     code_bank
                # ]

                tipo_cta = 'AHO' if x.bank_account_id.tipo_cuenta == 'Ahorro' else 'CTE'
                if x.partner_id.country_id.use_iban:
                    if not x.bank_account_id.iban_number:
                        raise ValidationError(_("Debes definir el # IBAN en la cuenta %s") % (x.bank_account_id.full_name,))
                if not x.bank_intermediary_id:
                    raise ValidationError(_("Debes definir un banco intermediario para pago en cuenta %s proveedor %s") % (x.bank_account_id.full_name,x.partner_id.name))
                fila = [
                    fit_field('PA', 2),  # Código de orientación
                    fit_field(obj.journal_id.bank_account_id.acc_number, 20),  # Cuenta empresa
                    i,  # Secuencial (numérico con ceros a la izquierda)
                    x.name,  # Comprobante de pago
                    obj.id,  # Contrapartida
                    fit_field('USD', 3),  # Moneda
                    str("{:.2f}".format(x.amount)).replace('.', ''),  # Valor
                    fit_field('CTA', 3),  # Forma de pago
                    fit_field(x.bank_account_id.bank_id.bic, 15),  # Swi ft banco beneficiario
                    fit_field(tipo_cta, 3),  # Tipo cuenta
                    fit_field(x.partner_id.country_id.use_iban and x.bank_account_id.iban_number or x.bank_account_id.acc_number, 34),  # Cuenta beneficiario
                    fit_field('N', 1),  # Tipo ID
                    fit_field('', 14),  # Campo en blanco
                    fit_field(obj.limpiar_texto(x.partner_id.name), 70),  # Nombre beneficiario
                    fit_field(obj.limpiar_texto(x.partner_id.street or '') , 70),  # Dirección
                    fit_field(obj.limpiar_texto(x.partner_id.phone or '') , 15),  # Teléfono
                    fit_field(x.partner_id.country_id.name_dscr_bank or x.partner_id.country_id.name or '', 22),  # Localidad
                    fit_field('', 1),  # Campo en blanco
                    fit_field((obj.limpiar_texto(x.comments or '') + " COMERCIAL OUR"), 200),  # Referencia
                    fit_field(x.bank_account_id.partner_id.email or '', 50),  # Email
                    fit_field('', 1),  # Campo en blanco
                    fit_field('105', 20),  # Motivo Económico
                    fit_field(pname or '', 20),  # Factura / RFB
                    fit_field(x.bank_intermediary_id.bic, 15),  # Banco Intermediario
                    fit_field('', 20),  # Extra 1
                    fit_field('', 10),  # Extra 2 (ej: fecha dd/mm/aaaa)
                ]


                writer.writerow(fila)

