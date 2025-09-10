# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID



class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_post(self):
        values=super(AccountPayment,self).action_post()
        self.update_employee_movement_lines()
        return values

    def action_draft(self):
        values=super(AccountPayment,self).action_draft()
        self.update_employee_movement_lines()
        return values

    def action_cancel(self):
        values=super(AccountPayment,self).action_cancel()
        self.update_employee_movement_lines()
        return values

    @api.constrains('state', 'move_id.state','reversed_payment_id')
    def update_employee_movement_lines(self):
        pass
        # for payment in self:
        #     #pass
        #     #payment.delete_payment_rel_purchases()
        #     if payment.state=='posted':
        #         if not payment.reversed_payment_id:
        #             # Verificar si el pago está vinculado a una o varias órdenes de compra
        #             purchases = payment.purchase_id if payment.purchase_id else False
        #             if purchases:
        #                 payment.payment_purchase_line_ids = [(5,),
        #                                                      (0,0,{
        #                                                         'order_id': purchases.id,
        #                                                         #'payment_id': payment.id,
        #                                                         'amount': payment.amount,
        #                                                     })  ]
        #         else:##si viene de una solicityd
        #             payment.payment_purchase_line_ids = [(5,)]
        #     else:  ##si viene de una solicityd
        #         payment.payment_purchase_line_ids = [(5,)]

