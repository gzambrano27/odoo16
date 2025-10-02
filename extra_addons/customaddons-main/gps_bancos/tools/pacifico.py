# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo import fields, _
from odoo.exceptions import ValidationError, UserError
from .macros_bancarias import macros_bancarias

class pacifico(macros_bancarias):

    def get_file_name_macro_local(self, obj):
        file_name = 'pago_pacifico_%s.txt' % (obj.name,)
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
            if 'pacifico' in journal_name:
                payment_name = obj.limpiar_texto(x.comments)[:20].ljust(20)
                tipo_cta = '10' if x.bank_account_id.tipo_cuenta == 'Ahorro' else '00'
                if obj.macro_bank_type == 'intrabancaria':
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
                            " " * 2 +  # localidad de retiro de cheque
                            " " * 2 +  # agencia retiro del cheque
                            tipo_identificacion.ljust(1) +  # Tipo de identificación (C/R/P)
                            identificacion.ljust(14) +  # Número identificación
                            ''.ljust(10)  # telefono del beneficiairo
                    )
                if obj.macro_bank_type == 'interbancaria':
                    codigos_bancos = obj.env.ref("l10n_ec.bank_7").get_all_codes()
                    if not codigos_bancos:
                        raise ValidationError(_("No hay codigos de bancos recuperados para PACIFICO"))
                    if not obj.journal_id.bank_account_id:
                        raise ValidationError(_("Diario no tiene configurado un # de Cuenta "))
                    bic = codigos_bancos.get(x.bank_account_id.bank_id.id, False)
                    if not bic:
                        raise ValidationError(
                            _("No hay código encontrado para PACIFICO para %s") % (
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
                            '00000'.ljust(15) +  # ?dentificación del Servicio
                            'PAGO PACIFICO'.ljust(20) +  # ?
                            'CU'.ljust(2) +  # Tipo de documento
                            'USD'.ljust(3) +  # Moneda
                            nombre_persona_pago[:30].ljust(30).replace("Ñ", "N").replace("ñ",
                                                                                         "n") +  # Nombre del beneficiario
                            " " * 2 +  # localidad de retiro de cheque
                            " " * 2 +  # agencia retiro del cheque
                            tipo_identificacion.ljust(1) +  # Tipo de identificación (C/R/P)
                            identificacion.ljust(14) +  # Número identificación
                            ''.ljust(10) +  # telefono del beneficiairo
                            ' ' +  # Tipo NUC del Ordenante
                            ''.ljust(14) +  # Número único del    Ordenante
                            ''.ljust(30) +  # Nombre del Ordenante del Cheque
                            ''.ljust(6) +  # Secuencial de número de lote
                            code_bank.ljust(2) +  # Código Banco
                            x.bank_account_id.acc_number.ljust(20)  # Número de Cuenta de Otros Bancos
                    )
                writer.writerow([fila])