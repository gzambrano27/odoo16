# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID



class ResPartner(models.Model):
    _inherit = "res.partner"

    group_category_id=fields.Many2one('account.partner.group.category',"Grupo de Categoria")

    enable_payment_bank_ids=fields.Many2many("res.bank","res_partner_bank_for_pay_rel",
                                            "partner_id","bank_id",
                                            "Registrados en el Banco",domain="[('use_macro_format','=',True)]")

    def name_get(self):
        result = []
        for partner in self:
            name = partner.name or ''
            if partner.vat:
                name = f"{name} - {partner.vat}"
            result.append((partner.id, name))
        return result

    @api.model
    def _get_domain_list_ids(self,context):
        line_ids=[]
        partner_ids = []
        if 'filter_by_bank' in context:
            if context.get("filter_by_bank", False):
                filter_bank_ids = context.get("filter_bank_ids", [])
                if filter_bank_ids:
                    self._cr.execute(
                            """ select partner_id,partner_id from res_partner_bank_for_pay_rel where bank_id in %s """ % (
                                tuple(filter_bank_ids + [-1, -1]),))
                    result = self._cr.fetchall()
                    partner_ids = result and [*dict(result)] or []
                    line_ids=partner_ids
        if "show_for_payment" in context:
            if context.get("show_for_payment", False):
                company_id = context.get("default_company_id", False)
                date_from = context.get("default_date_from", False)
                date_to = context.get("default_date_to", False)
                filter_docs=context.get('filter_docs','*')
                result = self.env["account.move"].sudo().search_query_cxp(company_id,
                                                                          date_from, date_to,
                                                                          partner_ids, 'show_partners',filter_docs)
                line_ids = result and [*dict(result)] or []
        return line_ids

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if not domain or domain is None:
            domain = []
        if self._context.get('origen')=='talento_humano' and self._context.get('type')=='inactive':
            domain += [('id', 'in', self.env['hr.employee'].sudo().search([]).mapped('partner_id').ids)]
        return super(ResPartner,self).search_read( domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        if self._context.get('origen') == 'talento_humano' and self._context.get('type') == 'inactive':
            # Filtrar contactos que sean empleados
            employee_ids = self.env['hr.employee'].sudo().search([]).mapped('address_home_id').ids
            args += [('id', 'in', employee_ids)]
        return super(ResPartner, self).name_search(
            name=name,
            args=args,
            operator=operator,
            limit=limit
        )

    @api.model
    def get_balance_partner(self,rows):
        total_residual = sum(row['amount_residual'] for row in rows if row['amount_residual'] is not None)
        return total_residual

    def get_balance_partner_lines(self, company_id):
        self.ensure_one()

        query = """
            SELECT 
    CASE 
    WHEN t.move_type = 'in_invoice' THEN 'Factura de Proveedor'
    WHEN t.move_type = 'out_invoice' THEN 'Factura de Cliente'
    WHEN t.move_type = 'in_refund' THEN 'NC de Proveedor'
    WHEN t.move_type = 'out_refund' THEN 'NC de Cliente'
    WHEN t.move_type = 'entry' THEN 'Asiento'
    WHEN t.move_type = 'in_receipt' THEN 'Recibo de Proveedor'
    WHEN t.move_type = 'out_receipt' THEN 'Recibo de Cliente'
    ELSE t.move_type END AS move_type_desc,
    t.DATE,
    t.COMPANY_ID,
    AM.NAME AS MOVE_NAME,
	AM.REF,
	T.DOC_ID,
    t.DEBIT,
    t.CREDIT,
    t.AMOUNT_RESIDUAL,
    SUM(t.AMOUNT_RESIDUAL) OVER (ORDER BY t.DOC_ID::INT) AS SALDO_ACUMULADO

FROM (
    SELECT 
        AM.MOVE_TYPE,
        AM.DATE,
        AM.COMPANY_ID,
        AM.ID AS DOC_ID,
        SUM(AML.DEBIT) AS DEBIT,
        SUM(AML.CREDIT) AS CREDIT,
        SUM(-1.00*AML.AMOUNT_RESIDUAL) AS AMOUNT_RESIDUAL

    FROM ACCOUNT_MOVE AM
        INNER JOIN ACCOUNT_MOVE_LINE AML ON AML.MOVE_ID = AM.ID AND ROUND(AML.CREDIT,2)>0.00 
        INNER JOIN ACCOUNT_ACCOUNT AA ON AA.ID = AML.ACCOUNT_ID
            AND AA.ACCOUNT_TYPE = 'liability_payable'

    WHERE
        AM.STATE = 'posted'
        AND AM.COMPANY_ID = %s 
        AND COALESCE(AML.PARTNER_ID, AM.PARTNER_ID) = %s 

    GROUP BY
        AM.MOVE_TYPE,
        AM.DATE,
        AM.COMPANY_ID,
        AM.ID
) t
INNER JOIN ACCOUNT_MOVE AM ON AM.ID=T.DOC_ID 
ORDER BY t.DOC_ID::INT;  """
        self._cr.execute(query, (company_id, self.id))
        return self._cr.dictfetchall()

    def get_anticipo_balance_partner_lines(self, company_id):
        self.ensure_one()

        query = """
            SELECT 
    CASE 
    WHEN t.move_type = 'in_invoice' THEN 'Factura de Proveedor'
    WHEN t.move_type = 'out_invoice' THEN 'Factura de Cliente'
    WHEN t.move_type = 'in_refund' THEN 'NC de Proveedor'
    WHEN t.move_type = 'out_refund' THEN 'NC de Cliente'
    WHEN t.move_type = 'entry' THEN 'Asiento'
    WHEN t.move_type = 'in_receipt' THEN 'Recibo de Proveedor'
    WHEN t.move_type = 'out_receipt' THEN 'Recibo de Cliente'
    ELSE t.move_type END AS move_type_desc,
    t.DATE,
    t.COMPANY_ID,
    AM.NAME AS MOVE_NAME,
	AM.REF,
    t.DEBIT,
    t.CREDIT,
    t.AMOUNT_RESIDUAL,
    SUM(t.AMOUNT_RESIDUAL) OVER (ORDER BY t.DOC_ID::INT) AS SALDO_ACUMULADO

FROM (
    SELECT 
        AM.MOVE_TYPE,
        AM.DATE,
        AM.COMPANY_ID,
        AM.ID AS DOC_ID,
        SUM(AML.DEBIT) AS DEBIT,
        SUM(AML.CREDIT) AS CREDIT,
        SUM(AML.AMOUNT_RESIDUAL) AS AMOUNT_RESIDUAL

    FROM ACCOUNT_MOVE AM
        INNER JOIN ACCOUNT_MOVE_LINE AML ON AML.MOVE_ID = AM.ID
        INNER JOIN ACCOUNT_ACCOUNT AA ON AA.ID = AML.ACCOUNT_ID
            AND AA.ACCOUNT_TYPE in ('liability_payable','asset_prepayments')

    WHERE
        AM.STATE = 'posted'
        AND AM.COMPANY_ID = %s
        AND COALESCE(AML.PARTNER_ID, AM.PARTNER_ID) = %s and AML.debit>0.00 
			and round(AML.AMOUNT_RESIDUAL,2)!=0.00

    GROUP BY
        AM.MOVE_TYPE,
        AM.DATE,
        AM.COMPANY_ID,
        AM.ID
) t
INNER JOIN ACCOUNT_MOVE AM ON AM.ID=T.DOC_ID 
ORDER BY t.DOC_ID::INT;
 """
        self._cr.execute(query, (company_id, self.id))
        result= self._cr.dictfetchall()
        return result

    def get_balance_partner_clte_lines(self, company_id):
        self.ensure_one()

        query = """
            SELECT 
    CASE 
    WHEN t.move_type = 'in_invoice' THEN 'Factura de Proveedor'
    WHEN t.move_type = 'out_invoice' THEN 'Factura de Cliente'
    WHEN t.move_type = 'in_refund' THEN 'NC de Proveedor'
    WHEN t.move_type = 'out_refund' THEN 'NC de Cliente'
    WHEN t.move_type = 'entry' THEN 'Asiento'
    WHEN t.move_type = 'in_receipt' THEN 'Recibo de Proveedor'
    WHEN t.move_type = 'out_receipt' THEN 'Recibo de Cliente'
    ELSE t.move_type END AS move_type_desc,
    t.DATE,
    t.COMPANY_ID,
    AM.NAME AS MOVE_NAME,
	AM.REF,
	T.DOC_ID,
    t.DEBIT,
    t.CREDIT,
    t.AMOUNT_RESIDUAL,
    SUM(t.AMOUNT_RESIDUAL) OVER (ORDER BY t.DOC_ID::INT) AS SALDO_ACUMULADO

FROM (
    SELECT 
        AM.MOVE_TYPE,
        AM.DATE,
        AM.COMPANY_ID,
        AM.ID AS DOC_ID,
        SUM(AML.DEBIT) AS DEBIT,
        SUM(AML.CREDIT) AS CREDIT,
        SUM(AML.AMOUNT_RESIDUAL) AS AMOUNT_RESIDUAL

    FROM ACCOUNT_MOVE AM
        INNER JOIN ACCOUNT_MOVE_LINE AML ON AML.MOVE_ID = AM.ID AND ROUND(AML.debit,2)>0.00 
        INNER JOIN ACCOUNT_ACCOUNT AA ON AA.ID = AML.ACCOUNT_ID
            AND AA.ACCOUNT_TYPE = 'asset_receivable'

    WHERE
        AM.STATE = 'posted'
        AND AM.COMPANY_ID = %s 
        AND COALESCE(AML.PARTNER_ID, AM.PARTNER_ID) = %s 

    GROUP BY
        AM.MOVE_TYPE,
        AM.DATE,
        AM.COMPANY_ID,
        AM.ID
) t
INNER JOIN ACCOUNT_MOVE AM ON AM.ID=T.DOC_ID 
ORDER BY t.DOC_ID::INT;  """
        self._cr.execute(query, (company_id, self.id))
        return self._cr.dictfetchall()

    def get_anticipo_balance_partner_clte_lines(self, company_id):
        self.ensure_one()

        query = """
            SELECT 
    CASE 
    WHEN t.move_type = 'in_invoice' THEN 'Factura de Proveedor'
    WHEN t.move_type = 'out_invoice' THEN 'Factura de Cliente'
    WHEN t.move_type = 'in_refund' THEN 'NC de Proveedor'
    WHEN t.move_type = 'out_refund' THEN 'NC de Cliente'
    WHEN t.move_type = 'entry' THEN 'Asiento'
    WHEN t.move_type = 'in_receipt' THEN 'Recibo de Proveedor'
    WHEN t.move_type = 'out_receipt' THEN 'Recibo de Cliente'
    ELSE t.move_type END AS move_type_desc,
    t.DATE,
    t.COMPANY_ID,
    AM.NAME AS MOVE_NAME,
	AM.REF,
    t.DEBIT,
    t.CREDIT,
    t.AMOUNT_RESIDUAL,
    SUM(t.AMOUNT_RESIDUAL) OVER (ORDER BY t.DOC_ID::INT) AS SALDO_ACUMULADO

FROM (
    SELECT 
        AM.MOVE_TYPE,
        AM.DATE,
        AM.COMPANY_ID,
        AM.ID AS DOC_ID,
        SUM(AML.DEBIT) AS DEBIT,
        SUM(AML.CREDIT) AS CREDIT,
        SUM(AML.AMOUNT_RESIDUAL) AS AMOUNT_RESIDUAL

    FROM ACCOUNT_MOVE AM
        INNER JOIN ACCOUNT_MOVE_LINE AML ON AML.MOVE_ID = AM.ID
        INNER JOIN ACCOUNT_ACCOUNT AA ON AA.ID = AML.ACCOUNT_ID
            AND AA.ACCOUNT_TYPE in ('asset_receivable','liability_current')

    WHERE
        AM.STATE = 'posted'
        AND AM.COMPANY_ID = %s
        AND COALESCE(AML.PARTNER_ID, AM.PARTNER_ID) = %s and AML.credit >0.00 
			and round(AML.AMOUNT_RESIDUAL,2)!=0.00

    GROUP BY
        AM.MOVE_TYPE,
        AM.DATE,
        AM.COMPANY_ID,
        AM.ID
) t
INNER JOIN ACCOUNT_MOVE AM ON AM.ID=T.DOC_ID 
ORDER BY t.DOC_ID::INT;
 """
        self._cr.execute(query, (company_id, self.id))
        result= self._cr.dictfetchall()
        return result

