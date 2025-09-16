# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError,UserError
import re

BANK_TYPE = [('checking', 'Corriente'), ('savings', 'Ahorros')]

class HrEmployee(models.Model):
    _inherit="hr.employee"

    bank_request_id=fields.Many2one('res.partner.bank.request','Solicitud de Creacion de Ctas.')

    def action_contact_create_validate(self):
        Partner = self.env['res.partner'].with_context(bypass_partner_restriction=True)
        Bank = self.env['res.partner.bank']
        BankRequest = self.env['res.partner.bank.request']
        Movement = self.env['hr.employee.movement']

        for employee in self:
            if not employee.identification_id:
                raise ValidationError(_("Debes definir el # de identificación"))

            # Datos de contacto
            partner_vals = {
                'name': employee.name,
                'email': employee.work_email or employee.private_email,
                'phone': employee.phone,
                'street': employee.private_street,
                'street2': employee.private_street2,
                'vat': employee.identification_id,
                'company_id': False,
                'l10n_latam_identification_type_id': employee.l10n_latam_identification_type_id.id if employee.l10n_latam_identification_type_id else False,
                'company_type': "person",
                'is_customer': True,
                'is_supplier': True,
                'country_id': employee.country_id.id if employee.country_id else False,
                'function': (employee.contract_id.job_id.name if employee.contract_id else employee.job_id.name)
            }

            # Validar cuenta y preparar datos bancarios
            bank_vals = {}
            if employee.pay_with_transfer:
                Movement.validate_acc_numbers(employee.account_number, employee)
                bank_vals = {
                    'bank_id': employee.bank_id.id,
                    'acc_number': employee.account_number,
                    'tipo_cuenta': 'Corriente' if employee.bank_type == 'checking' else 'Ahorro',
                    'currency_id': employee.company_id.currency_id.id,
                    'acc_holder_name': employee.name,
                    'tercero': employee.tercero,
                    'identificacion_tercero': employee.identificacion_tercero,
                    'nombre_tercero': employee.nombre_tercero,
                    'l10n_latam_identification_tercero_id': employee.l10n_latam_identification_tercero_id.id if employee.l10n_latam_identification_tercero_id else False,
                    'partner_email': employee.work_email or employee.private_email,
                    'company_id': employee.company_id.id,
                    #'allow_out_payment': True,
                    'active': True,
                    'origen': 'talento_humano',
                    'employee_id':employee.id,
                }

            # Buscar o crear contacto
            partner = employee.work_contact_id.with_context(bypass_partner_restriction=True)
            if not partner:
                partners = Partner.sudo().search([('vat', '=', employee.identification_id)])
                if not partners:
                    try:
                        partner = Partner.with_context(bypass_partner_restriction=True).create(partner_vals)
                        self.env.user.notify_info("Contacto creado correctamente")
                    except Exception as e:
                        raise ValidationError(f"Error al crear el contacto: {str(e)}")
                elif len(partners) == 1:
                    partner = partners[0].with_context(bypass_partner_restriction=True)
                    partner.write(partner_vals)
                    self.env.user.notify_info("Contacto actualizado correctamente")
                else:
                    raise ValidationError(
                        f"Existen más de un contacto con identificación {employee.identification_id}, nombre {employee.name}")
            else:
                partner.with_context(bypass_partner_restriction=True).write(partner_vals)
                self.env.user.notify_info("Contacto actualizado correctamente")

            # Enlace o creación de cuenta o solicitud
            update_vals = {'partner_id': partner.id}

            if bank_vals:
                bank_vals['partner_id'] = partner.id

                bank = Bank.search([
                    ('partner_id', '=', partner.id),
                    ('bank_id', '=', employee.bank_id.id),
                    ('acc_number', '=', employee.account_number)
                ])

                if bank:
                    if len(bank) > 1:
                        raise ValidationError(_("Existe más de una cuenta bancaria con %s / %s") % (
                            employee.bank_id.name, employee.account_number))
                    update_vals['bank_account_id'] = bank.id
                else:
                    # Crear solicitud
                    bank_request = BankRequest.search([
                        ('partner_id', '=', partner.id),
                        ('bank_id', '=', employee.bank_id.id),
                        ('acc_number', '=', employee.account_number),
                        ('type','=','created')
                    ])
                    if not bank_request:
                        bank_request = BankRequest.create(bank_vals)
                        bank_request.action_send()
                        note_subtype = self.env.ref('mail.mt_note')
                        bank_request.message_post(
                            body="Se adjunta certificado bancario.",
                            attachment_ids=employee.certificado_bancario_attch_ids.ids,
                            subtype_id=note_subtype.id,
                        )
                    update_vals['bank_request_id'] = bank_request.id


            employee._write(update_vals)

        return True
