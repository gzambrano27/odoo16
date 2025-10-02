# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo import fields, _
from odoo.exceptions import ValidationError, UserError

import re
from .macros_bancarias import macros_bancarias

class pichincha(macros_bancarias):

    def get_file_name_macro_local(self, obj):
        file_name = 'pago_pichincha_%s.txt' % (obj.name,)
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
            #####################################################banco pichincha#####################################################3
            if 'pichincha' in journal_name:
                codigos_bancos = obj.env.ref("l10n_ec.bank_2").get_all_codes()
                if not codigos_bancos:
                    raise ValidationError(_("No hay codigos de bancos recuperados para PICHINCHA"))
                tipo_cta = 'AHO' if x.bank_account_id.tipo_cuenta == 'Ahorro' else 'CTE'
                # code_bank = 'CUE001'.ljust(8) if row_data['bank_code'] == '37' else 'COB001'.ljust(8)
                # forma_pago = 'CUE' if str(x.employee_id.bank_id.bic) == '37' else 'COB'
                # code_bank = str(x.employee_id.bank_id.bic)
                bic = codigos_bancos.get(x.bank_account_id.bank_id.id, False)
                if not bic:
                    raise ValidationError(
                        _("No hay código encontrado para PICHINCHA para %s") % (x.bank_account_id.bank_id.name,))

                forma_pago = 'CUE' if bic == '37' else 'COB'
                code_bank = bic
                payment_name = obj.limpiar_texto(x.comments)[:60].ljust(60)
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
