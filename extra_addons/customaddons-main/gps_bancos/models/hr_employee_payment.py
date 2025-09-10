# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class HrEmployeePayment(models.Model):
    _inherit = "hr.employee.payment"

    request_type_id = fields.Many2one('account.payment.request.type', 'Tipo de Solicitud')

    def _get_account_noiess_id(self,account_partner):
        self.ensure_one()
        OBJ_CONFIG = self.env["account.configuration.payment"].sudo()

        brw_conf = OBJ_CONFIG.search([
            ('company_id', '=', self.company_id.id)
        ])
        if not brw_conf:
            raise ValidationError(_("No hay configuracion de pagos para %s ") % (self.company.name,))

        return brw_conf.local_prepayment_account_id.id

    def get_partner_account_id(self):
        self.ensure_one()
        brw_each=self
        employee_name=''
        if not brw_each.pay_with_transfer:
            return False
        partner_ids=self.env["res.partner"]
        if brw_each.movement_ids:
            employee = brw_each.movement_line_ids.mapped('employee_id')
            employee_name=employee.name
            afiliado = brw_each.movement_ids.mapped('filter_iess')[0]
            if afiliado:
                partner_ids = employee.partner_id
                print("afiliado",partner_ids.id, partner_ids.name)
            else:
                partner_ids = employee.partner_id
                if employee.tiene_ruc:
                    partner_ids = employee.ruc_partner_id
                print("no afiliado",partner_ids.id, partner_ids.name)
        if brw_each.payslip_ids:
            employee = brw_each.payslip_line_ids.mapped('employee_id')
            employee_name = employee.name
            afiliado = brw_each.payslip_ids.mapped('type_struct_id.legal_iess')[0]
            if afiliado:
                partner_ids = employee.partner_id
                print("afiliado",partner_ids.id, partner_ids.name)
            else:
                partner_ids = employee.partner_id
                if employee.tiene_ruc:
                    partner_ids = employee.ruc_partner_id
                print("no afiliado",partner_ids.id, partner_ids.name)
        if not partner_ids:
            raise ValidationError(_("No hay contactos encontrados para %s") % (employee_name,))
        if len(partner_ids) > 1:
            raise ValidationError(_("Hay mas de un contacto definido,solo debe ser uno"))
        print(partner_ids)
        return partner_ids.id

    def action_create_request(self):
        for brw_each in self:
            brw_request_type=self.env.ref('gps_bancos.req_type_nomina')
            description_motives=[]
            main_movements=[]
            partner_ids=self.env["res.partner"]
            employee_name = ''
            if brw_each.movement_ids:
                main_movements=brw_each.movement_ids.mapped('name')
                description_motives1 = brw_each.movement_line_ids.mapped('name')
                description_motives2 = brw_each.movement_line_ids.mapped('employee_id.name')
                description_motives = description_motives1 + description_motives2
                employee = brw_each.movement_line_ids.mapped('employee_id')
                employee_name=employee.name
                brw_request_type = brw_each.movement_ids.mapped('rule_id.request_type_id')
                afiliado = brw_each.movement_ids.mapped('filter_iess')[0]
                if afiliado:
                    partner_ids=employee.partner_id
                else:
                    partner_ids=employee.partner_id
                    if employee.tiene_ruc:
                        partner_ids = employee.ruc_partner_id
            if brw_each.payslip_ids:
                main_movements = brw_each.payslip_ids.mapped('name')
                description_motives = brw_each.payslip_line_ids.mapped('name')
                employee = brw_each.payslip_line_ids.mapped('employee_id')
                employee_name = employee.name
                brw_request_type = self.env.ref('gps_bancos.req_type_nomina')
                afiliado=brw_each.payslip_ids.mapped('type_struct_id.legal_iess')[0]
                if afiliado:
                    partner_ids=employee.partner_id
                else:
                    partner_ids = employee.partner_id
                    if employee.tiene_ruc:
                        partner_ids = employee.ruc_partner_id
            if not partner_ids:
                raise ValidationError(_("No hay contactos encontrados para %s") % (employee_name,))
            if len(partner_ids) > 1:
                raise ValidationError(_("Hay mas de un contacto definido,solo debe ser uno"))


            description_motives = ','.join(description_motives)
            main_movements = ','.join(main_movements)
            brw_request=self.env["account.payment.request"].sudo().create({
                "origin":"automatic",
                "type":"hr.employee.payment",
                "type_document":"document",
                "quota":1,
                "company_id":brw_each.company_id.id,
                "payment_employee_id": brw_each.id,
                "partner_id":partner_ids.id,
                "description_motive":description_motives,
                "document_ref": main_movements,
                'date_maturity': brw_each.date_process,
                'date': brw_each.date_process,
                "amount": brw_each.total,
                "amount_original": brw_each.total,
                "request_type_id":brw_request_type.id,
                'type_module':'payslip',
                "default_mode_payment":brw_each.pay_with_transfer and "bank" or "check"
            })
            brw_request.action_confirmed()
            brw_request.write({"checked":True})
        return True

    def action_cancel_request(self):
        for brw_each in self:
            request_srch=self.env["account.payment.request"].sudo().search([('payment_employee_id','=',brw_each.id)])
            if request_srch:
                request_srch.action_cancelled()

        return True

    def action_multi_paid(self):
        pass