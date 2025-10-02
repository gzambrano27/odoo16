# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo import fields, _
from odoo.exceptions import ValidationError, UserError

from .macros_bancarias import macros_bancarias

class bolivariano(macros_bancarias):

    def get_file_name_macro_local(self,obj):
        file_name = 'pago_bol_%s.biz' % (obj.name,)
        return file_name

    def generate_file_macro_local(self,obj,writer,journal_name,brw_company):
        i = 1
        company = brw_company.name
        codbanco=''
        if company == 'IMPORT GREEN POWER TECHNOLOGY, EQUIPMENT & MACHINERY ITEM S.A':
            codbanco = '11074'  # Verificar!
        if company == 'GREEN ENERGY CONSTRUCTIONS & INTEGRATION C&I SA':
            codbanco = '11100'  # Verificar!
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
            if 'bolivariano' in journal_name:
                codigos_bancos = obj.env.ref("l10n_ec.bank_12").get_all_codes()
                if not codigos_bancos:
                    raise ValidationError(_("No hay codigos de bancos recuperados para BOLIVARIANO"))
                bic = codigos_bancos.get(x.bank_account_id.bank_id.id, False)
                if not bic:
                    raise ValidationError(
                        _("No hay código encontrado para BOLIVARIANO para %s") % (x.bank_account_id.bank_id.name,))
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
                        obj.limpiar_texto(x.comments)[:60].ljust(60) +  # 151-210
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


