# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime


class AccountConfigurationPayment(models.Model):
    _name = 'account.configuration.payment'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Configuraciones de Pagos"

    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company
    )
    day_id=fields.Many2one("calendar.day","Dia de Pago",required=True,tracking=True)

    bank_conf_ids=fields.One2many('account.configuration.payment.bank','conf_payment_id','Configuraciones del Banco')
    journal_ids=fields.Many2many('account.journal','account_conf_payment_all_journal_rel','conf_payment_id','journal_id','Diarios',tracking=True)
    active=fields.Boolean("Activo",default=True,tracking=True)

    local_prepayment_account_id=fields.Many2one('account.account','Cuenta de Anticipos Locales',tracking=True)
    exterior_prepayment_account_id = fields.Many2one('account.account', 'Cuenta de Anticipos Exterior',tracking=True)

    validate_with_base_amount=fields.Boolean("Validar con Base Imponible",default=True,tracking=True)
    lock_payment_with_base_amount=fields.Boolean("Bloquear pago con excedente",default=True,tracking=True)

    first_bond_issuance_acct_id=fields.Many2one("account.account","Cuenta Primera Obligacion")
    second_bond_issuance_acct_id = fields.Many2one("account.account", "Cuenta Segunda Obligacion")
    third_bond_issuance_acct_id = fields.Many2one("account.account", "Cuenta Tercera Obligacion")

    int_first_bond_issuance_acct_id = fields.Many2one("account.account", "Cuenta Interés Primera Obligacion")
    int_second_bond_issuance_acct_id = fields.Many2one("account.account", "Cuenta Interés Segunda Obligacion")
    int_third_bond_issuance_acct_id = fields.Many2one("account.account", "Cuenta Interés Tercera Obligacion")

    payment_overdue_interest_acct_id = fields.Many2one("account.account", "Cuenta Interés Mora")
    payment_other_acct_id =  fields.Many2one("account.account", "Cuenta Otros Gastos")

    prestamo_capital_acct_id = fields.Many2one("account.account", "Cuenta Capital Prestamos")
    prestamo_interes_acct_id = fields.Many2one("account.account", "Cuenta Interes Prestamos")
    prestamo_interes_mora_acct_id = fields.Many2one("account.account", "Cuenta Interes Mora")
    prestamo_otros_acct_id = fields.Many2one("account.account", "Cuenta otros Prestamos")

    liquidation_account_id=fields.Many2one("account.account", "Cuenta Liquidacion de Haberes")

    group_by_employee_payment=fields.Boolean('Agrupar Pagos',default=True)

    _rec_name="company_id"

    _check_company_auto = True
