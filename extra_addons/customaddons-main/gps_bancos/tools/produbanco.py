# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo import fields, _
from odoo.exceptions import ValidationError, UserError

import re
from .macros_bancarias import macros_bancarias

class produbanco(macros_bancarias):

    def get_file_name_macro_local(self, obj):
        file_name = 'pago_produbanco_%s.txt' % (obj.name,)
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
            if 'produbanco' in journal_name:
                codigos_bancos = obj.env.ref("l10n_ec.bank_11").get_all_codes()
                if not codigos_bancos:
                    raise ValidationError(_("No hay codigos de bancos recuperados para PRODUBANCO"))
                if not obj.journal_id.bank_account_id:
                    raise ValidationError(_("Diario no tiene configurado un # de Cuenta "))
                tipo_cta = 'AHO' if x.bank_account_id.tipo_cuenta == 'Ahorro' else 'CTE'
                # code_bank = 'CUE001'.ljust(8) if row_data['bank_code'] == '37' else 'COB001'.ljust(8)
                # forma_pago = 'CUE' if str(x.employee_id.bank_id.bic) == '37' else 'COB'
                # code_bank = str(x.employee_id.bank_id.bic)
                bic = codigos_bancos.get(x.bank_account_id.bank_id.id, False)
                if not bic:
                    raise ValidationError(
                        _("No hay código encontrado para PRODUBANCO para %s") % (
                            x.bank_account_id.bank_id.name,))

                forma_pago = 'CUE' if bic == '37' else 'COB'
                code_bank = bic
                payment_name = obj.limpiar_texto(x.comments)[:200].ljust(200)
                pname = re.sub(r'[^0-9]', '', payment_name.replace('.', ''))
                codpago = re.sub(r'[^0-9]', '', pname)
                # 045-104
                fila = [
                    'PA',  # Código Orientación
                    obj.journal_id.bank_account_id.acc_number.zfill(11),  ##Cuenta Empresa
                    str(i).zfill(7),  # Secuencial Pago
                    str(x.id),  # Comprobante de Pago
                    identificacion,  # Contrapartida
                    'USD',  # mONEDA
                    str("{:.2f}".format(x.amount)).replace('.', '').zfill(11),  # Valor
                    'CTA',  # Forma de Pago
                    code_bank.zfill(4),  # Código de Institución Financiera
                    tipo_cta,  # Tipo de Cuenta
                    x.bank_account_id.acc_number.zfill(11),  # Número d Cuenta
                    tipo_identificacion,  # Tipo ID Cliente
                    identificacion,  # Número ID Cliente Beneficiario
                    nombre_persona_pago[:60].ljust(60).replace("Ñ", "N").replace("ñ", "n"),  # Nombre del Cliente
                    '',  # Dirección Beneficiario
                    '',  # Ciudad Beneficiario
                    '',  # Teléfono Beneficiario
                    'GUAYAQUIL',  # Localidad de pago
                    payment_name,  # Referencia
                    x.bank_account_id.partner_email and 'PAGOS VARIOS| ' + x.bank_account_id.partner_email or 'PAGOS VARIOS'
                    # Referencia Adicional
                ]
                writer.writerow(fila)
