# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class HrEmployeeLiquidation(models.Model):
    _inherit = "hr.employee.liquidation"

    request_type_id = fields.Many2one('account.payment.request.type', 'Tipo de Solicitud')

    checked=fields.Boolean("Firma de Empleado",default=False)

    def write(self, vals):
        res = super().write(vals)
        if 'checked' in vals:
            for record in self:
                requests = self.env['account.payment.request'].search([
                    ('liquidation_employee_id', '=', record.id)
                ])
                requests.write({'checked': vals['checked']})
        return res

    @api.model
    def create(self, vals):
        record = super().create(vals)
        if 'checked' in vals:
            requests = self.env['account.payment.request'].search([
                ('liquidation_employee_id', '=', record.id)
            ])
            requests.write({'checked': vals['checked']})
        return record

    def action_create_request(self):
        for brw_each in self:
            if brw_each.total <= 0:
                continue
            partner_ids=brw_each.employee_id.partner_id
            if not partner_ids:
                raise ValidationError(_("No hay contactos encontrados"))
            if len(partner_ids)>1:
                raise ValidationError(_("Hay mas de un contacto definido,solo debe ser uno"))
            brw_request_type=self.env.ref('gps_bancos.req_type_finiquitos')
            description_motives = brw_each.name
            main_movements = brw_each.name
            srch_request=self.env["account.payment.request"].sudo().search([('type','=','hr.employee.liquidation'),
                                                                            ('liquidation_employee_id','=',brw_each.id),
                                                                            ('state','!=','cancelled')
                                                                            ])
            if not srch_request:
                srch_request.action_cancelled()
            brw_request=self.env["account.payment.request"].sudo().create({
                    "origin":"automatic",
                    "type":"hr.employee.liquidation",
                    "type_document":"document",
                    "quota":1,
                    "company_id":brw_each.company_id.id,
                    "liquidation_employee_id": brw_each.id,
                    "partner_id":partner_ids.id,
                    "description_motive":description_motives,
                    "document_ref": main_movements,
                    'date_maturity': brw_each.date_for_payment,
                    'date': brw_each.date_process,##fecha de cuando realiza la fecha
                    "amount": brw_each.total,
                    "amount_original": brw_each.total,
                    "request_type_id":brw_request_type.id,
                    'type_module':'payslip',
                    'default_mode_payment':brw_each.pay_with_transfer and 'bank' or 'check',
                    'default_mode_nomina_payment': brw_each.pay_with_transfer and 'bank' or 'check'
                })
            brw_request.action_confirmed()
        return True

    def action_cancel_request(self):
        for brw_each in self:
            request_srch=self.env["account.payment.request"].sudo().search(
                [('liquidation_employee_id','=',brw_each.id)])
            if request_srch:
                request_srch.action_cancelled()
            brw_each.write({"checked":False})
        return True

    def update_account_to_pay(self,account_ids):
        DEC=2
        if account_ids is None:
            account_ids=[]
        brw_conf=self.company_id.get_payment_conf()
        if not  brw_conf.liquidation_account_id:
            raise ValidationError(_("No se ha difinido cuenta para finiquitos por pagar en %s") % (brw_conf.company_id.name,))
        if self.total>0:
            account_ids.append((0,0,{
                "account_id": brw_conf.liquidation_account_id.id,
                "debit": 0,
                "credit": round(self.total,DEC),
                "locked": True,
                    "origin":"automatic"
            }))
        return account_ids

    def action_cancel_move(self):
        for brw_each in self:
            if brw_each.move_id:
                if brw_each.move_id.state != 'cancel':
                    brw_each.move_id.button_cancel()
        return True

    def action_reverse_sended(self):
        self.action_cancel_move()
        self.action_cancel_request()
        for brw_each in self:
            brw_each.write({"state":"approved"})
        return True