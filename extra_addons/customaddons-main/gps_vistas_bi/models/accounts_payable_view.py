from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountsPayableView(models.Model):
    _name = 'accounts.payable.view'
    _description = 'Vista de Cuentas por Pagar'
    _auto = False

    id = fields.Integer(string="ID", readonly=True)

    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    company_name = fields.Char(string="Company Name", readonly=True)

    partner_id = fields.Many2one("res.partner", string="Partner", readonly=True)
    partner_name = fields.Char(string="Partner Name", readonly=True)

    move_id = fields.Many2one("account.move", string="Asiento", readonly=True)

    move_name = fields.Char(string="Move Name", readonly=True)
    move_ref = fields.Char(string="Reference", readonly=True)
    move_date = fields.Date(string="Move Date", readonly=True)

    date_maturity = fields.Date(string="Due Date", readonly=True)

    debit = fields.Monetary(string="Debit", readonly=True)
    credit = fields.Monetary(string="Credit", readonly=True)

    account_code = fields.Char(string="Account Code", readonly=True)
    account_name = fields.Char(string="Account Name", readonly=True)

    amount_residual = fields.Monetary(string="Residual Amount", readonly=True)

    currency_id = fields.Many2one(
        "res.currency", string="Currency",
        readonly=True, default=lambda self: self.env.company.currency_id.id
    )
    type = fields.Selection([('asiento', 'Documento'),
                             ('emision', 'Emisión'),
                             ('obligacion', 'Obligación'),

                             ], string="Tipo")

    def init(self):
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW accounts_payable_view AS (
              
               SELECT
    aml.id,
    rc.id as company_id,
	rc.name as company_name,
	rp.id as partner_id,
	rp.name as partner_name,
	am.id as move_id,
	am.name as move_name,
	am.ref as move_ref,
	am.date as move_date,
	aml.date_maturity,
	aml.debit,
	aml.credit,
	aa.code as account_code,
	aa.name as account_name,
	aml.amount_residual as amount_residual ,
	coalesce(am.currency_id,rc.currency_id ) as currency_id ,
	'asiento'::varchar as type

from account_move_line aml
	inner join account_move am on am.id=aml.move_id
	inner join account_account aa on aa.id=aml.account_id
	inner join res_partner rp on rp.id=coalesce(aml.partner_id,am.partner_id)
	inner join res_company rc on rc.id=am.company_id 
where am.state='posted'

	and round(aml.amount_residual,2)!=0.00
	and aa.ACCOUNT_TYPE='liability_payable'
              
              )
        """)

    _order="company_id asc,move_id desc"