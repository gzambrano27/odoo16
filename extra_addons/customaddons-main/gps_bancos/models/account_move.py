# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
from ...message_dialog.tools import FileManager
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager

fileO = FileManager()
dateO = DateManager()
calendarO = CalendarManager()
from datetime import datetime, timedelta


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _get_prepayment_aml_account_payable_id(self):
        inv = self
        """
            Devuelve la cuenta contable de tipo 'payable' desde las líneas contables.
            """
        if not self.line_ids:
            raise ValidationError(_("No hay líneas contables disponibles."))

        line = self.line_ids.filtered(
            lambda l: l.account_id.account_type == 'liability_payable'
        )[:1]

        if not line:
            raise ValidationError(_("No se encontró una cuenta contable de tipo 'payable'."))

        return line.account_id.id

    @api.model
    def _get_prepayment_aml_account_receivable_id(self):
        """
            Devuelve la cuenta contable de tipo 'receivable' desde las líneas contables.
            """
        if not self.line_ids:
            raise ValidationError(_("No hay líneas contables disponibles."))

        line = self.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable'
        )[:1]

        if not line:
            raise ValidationError(_("No se encontró una cuenta contable de tipo 'receivable'."))

        return line.account_id.id

    def action_post(self):
        values=super(AccountMove,self).action_post()
        for brw_each in self:
            purchase_orders = brw_each.invoice_line_ids.mapped('purchase_line_id.order_id')
            if purchase_orders:
                purchase_orders.liberate_requests_payments()
                #purchase_orders.reconcile_automatics(brw_each)
            brw_each.write({"date_approved":fields.Datetime.now()})
            brw_each.send_mail_not_partner_bank()
        return values

    def button_draft(self):
        values=super(AccountMove,self).button_draft()
        for brw_each in self:
            brw_each.liberate_requests_payments()
            brw_each.write({"date_approved":None})
        return values

    def button_cancel(self):
        values=super(AccountMove,self).button_cancel()
        for brw_each in self:
            brw_each.liberate_requests_payments()
            brw_each.write({"date_approved": None})
        return values

    def liberate_requests_payments(self):
        for brw_each in self:
            srch = self.env["account.payment.request"].search([('company_id', '=', brw_each.company_id.id),
                                                               ('type', '=', 'account.move'),
                                                               ('invoice_line_id', 'in', brw_each.line_ids.ids),
                                                               ('state', '=', ('draft','paid')),
                                                               ('paid', '<=', 0.00)
                                                            ])
            if srch:
                srch.action_cancelled()
            return True

    date_approved=fields.Datetime(string="Fecha Aprobado",default=None)

    def _where_cal(self, domain=None):
        if domain is None:
            domain = []
        if self._context.get("show_for_payment", False):
            company_id = self._context.get("default_company_id", False)
            date_from = self._context.get("default_date_from", False)
            date_to = self._context.get("default_date_to", False)
            partner_ids = self._context.get("default_partner_ids", []) or []
            tipo = self._context.get("default_show_options", False)
            filter_docs = self._context.get("filter_docs", '*')
            not_show_ids=self._context.get("not_show_ids", [])
            not_request_id=self._context.get('not_request_id',False)
            filter_account_ids = []
            if not_request_id:
                brw_request=self.env["account.payment.analysis.request.wizard"].sudo().browse(not_request_id)
                not_show_ids+=brw_request.request_line_ids.mapped('invoice_line_id').ids
                print('not_show_ids',not_show_ids)
                ###########buscar otras solicitudes abiertas
                srch_requests = self.env["account.payment.request"].sudo().search(
                    [('company_id', '=', brw_request.company_id.id),
                     ('state', 'not in', ('cancelled', 'locked', 'done')),
                     ('invoice_line_id', '!=', False)
                     ])
                not_show_ids += srch_requests.mapped('invoice_line_id').ids
                filter_account_ids = brw_request.get_filter_account_ids()

            ###########buscar otras solicitudes abiertas
            result = self.search_query_cxp(company_id, date_from, date_to, partner_ids, tipo, filter_docs,not_show_ids,filter_account_ids=filter_account_ids)
            line_ids = result and list(dict(result)) or [-1, -1]
            domain = [('id', 'in', line_ids)] + domain
        return domain

    def _compute_quota(self):
        values={}
        for move in self:
            if move.move_type!='entry':
                # Filtrar líneas con fecha de vencimiento
                lines_with_maturity = move.line_ids.filtered(lambda l: l.date_maturity).sorted(
                    key=lambda l: l.date_maturity)

                # Asignar número de cuota según el orden
                for index, line in enumerate(lines_with_maturity, start=1):
                    values[line] = index
        return values

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = self._where_cal(domain)
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def search_query_cxp(self,company_id,date_from,date_to,partner_ids,tipo,filter_docs,not_show_ids,filter_account_ids=[]):
        QUERY_TYPES={
            "show_lines":"""select invoice_line_id,invoice_line_id from detalle_asientos GROUP BY invoice_line_id""",
            "show_invoices":"""select invoice_id,invoice_id from detalle_asientos group by invoice_id """,
            'show_partners':'''select partner_id,partner_id from detalle_asientos group by partner_id '''
        }
        #,'{tipo}'::varchar AS tipo_prueba /* create_requests, show_lines, show_invoices */
        query_final=QUERY_TYPES[tipo]
        WHERE_DATE= " "
        if date_from:
            WHERE_DATE+= f" AND COALESCE(aml.date_maturity, am.date, NOW()::DATE)>='{date_from}' "
        if date_to:
            WHERE_DATE+= f" AND COALESCE(aml.date_maturity, am.date, NOW()::DATE)<='{date_to}' "
        query=f""";WITH variables AS (
    SELECT 
        {company_id}::int AS company_id, 
        ARRAY{partner_ids}::int[] AS partner_ids ,
        '{filter_docs}'::varchar as filter_docs ,
        ARRAY{not_show_ids}::int[] AS not_show_ids,
        ARRAY{filter_account_ids}::int[] AS filter_account_ids
), 
not_show_ids_table AS (
    SELECT unnest(v.not_show_ids) AS id
    FROM variables v
),
filter_account_table AS (
    SELECT unnest(v.filter_account_ids) AS account_id
    FROM variables v
),
resumen AS (
    SELECT 
        am.id AS invoice_id,
        aml.id AS invoice_line_id, 
        COALESCE(aml.date_maturity, am.date, NOW()::DATE) AS date_maturity,
        ROW_NUMBER() OVER (
            PARTITION BY am.id 
            ORDER BY COALESCE(aml.date_maturity, am.date, NOW()::DATE) ASC
        ) AS quota  
    FROM account_move am
    INNER JOIN variables ON am.company_id = variables.company_id     
    INNER JOIN account_move_line aml 
        ON aml.move_id = am.id 
        AND am.state = 'posted'  
        AND aml.credit > 0                   
    INNER JOIN account_account aa 
        ON aa.id = aml.account_id 
        AND aa.account_type = 'liability_payable' 	 
    left join filter_account_table fat on fat.account_id=aml.account_id 					
    WHERE am.state = 'posted' 
        AND aml.partner_id IS NOT NULL  and aml.id   not in (select ns.id from not_show_ids_table ns) AND (
           cardinality(variables.filter_account_ids) = 0 
	        OR (
	            cardinality(variables.filter_account_ids) > 0 
	            AND aml.account_id = ANY(variables.filter_account_ids)
	        )
        ) 
),
detalle_asientos as (
	SELECT 
    aml.id AS invoice_line_id,
    aml.move_id AS invoice_id,
    am.company_id,
    ABS(aml.amount_residual) AS amount_residual,
    aml.credit,
    aml.debit,
    am.invoice_payment_term_id,
    COALESCE(aml.partner_id, am.partner_id) AS partner_id,
    COALESCE(aml.date_maturity, am.date, NOW()::DATE) AS date_maturity,
    r.quota  
	FROM account_move am
	INNER JOIN variables ON am.company_id = variables.company_id     
	INNER JOIN account_move_line aml 
	    ON aml.move_id = am.id 
	    AND am.state = 'posted' 
	    AND aml.credit > 0   
	    { WHERE_DATE }  
	INNER JOIN resumen r ON r.invoice_line_id = aml.id	
	INNER JOIN account_account aa 
	    ON aa.id = aml.account_id 
	    AND aa.account_type = 'liability_payable' 		
	LEFT JOIN l10n_latam_document_type ldtt on ldtt.id=am.l10n_latam_document_type_id  
	WHERE am.state = 'posted' 
	    AND aml.amount_residual != 0.00 
	    AND aml.partner_id IS NOT NULL 
	    AND (
	        cardinality(variables.partner_ids) = 0 
	        OR (
	            cardinality(variables.partner_ids) > 0 
	            AND COALESCE(aml.partner_id, am.partner_id) = ANY(variables.partner_ids)
	        )
	    ) and 
		(
			(variables.filter_docs='*' and coalesce(ldtt.code,'')!='03' ) 
			    or 
			( variables.filter_docs!='*' and coalesce(ldtt.code,'')=variables.filter_docs )
		) 
)

{query_final}"""
        self._cr.execute(query)
        result=self._cr.fetchall()
        return result

    @api.model
    def search_query_moves(self, type,line_ids):
        filter=type=="moves" and " AND AM.ID IN %s " % (tuple(line_ids),) or " AND AML.ID IN %s " % (tuple(line_ids),)
        final_query=type=="lines" and " SELECT *,array[]::integer[] as invoice_line_ids FROM resumen " or """ SELECT invoice_payment_term_id,invoice_id,company_id,
	sum(amount_residual) as amount_residual,sum(credit) as credit,sum(debit) as debit,
    ARRAY_AGG(invoice_line_id) AS invoice_line_ids,
	max(quota) as quota,
	max(date_maturity) as date_maturity,
	null as invoice_line_id ,
	partner_id  ,invoice_name 
	FROM resumen
group by invoice_payment_term_id,invoice_id,company_id,partner_id,invoice_name  """
        query = f""";WITH resumen AS ( 
	SELECT 
            am.id AS invoice_id,
            aml.id AS invoice_line_id, 
            COALESCE(aml.date_maturity, am.date, NOW()::DATE) AS date_maturity,
            ROW_NUMBER() OVER (
                PARTITION BY am.id 
                ORDER BY COALESCE(aml.date_maturity, am.date, NOW()::DATE) ASC
            ) AS quota,
			 am.company_id,
	        ABS(aml.amount_residual) AS amount_residual,
	        aml.credit,
	        aml.debit,
	        am.invoice_payment_term_id,
	        coalesce(aml.partner_id,am.partner_id) as partner_id ,
	        am.name as invoice_name 
        FROM account_move am
        INNER JOIN account_move_line aml 
            ON aml.move_id = am.id 
            AND am.state = 'posted'  
            AND aml.credit > 0                   
        INNER JOIN account_account aa 
            ON aa.id = aml.account_id 
            AND aa.account_type = 'liability_payable' 								
        WHERE am.state = 'posted' 
            AND aml.partner_id IS NOT NULL and aml.amount_residual!=0.00 
			{filter}
)
   {final_query}"""
        self._cr.execute(query)
        result = self._cr.dictfetchall()
        return result

    def send_mail_not_partner_bank(self):
        template = self.env.ref('gps_bancos.email_template_partner_no_bank', raise_if_not_found=False)
        for brw_each in self:
            if brw_each.move_type in ('in_invoice','in_refund'):
                bank_accounts = brw_each.partner_id.bank_ids.filtered(lambda x: x.active)
                if not bank_accounts and template:
                    template.send_mail(brw_each.id, force_send=True)
        return True

    def get_mail_bank_alert_not(self):
        self.ensure_one()
        return self.company_id.get_mail_bank_alert_not()

    def get_applied_moves(self):
        moves = self.env['account.move']
        for brw_each in self:
            # Filtramos las líneas 'payable'
            payable_lines = brw_each.line_ids.filtered(lambda l: l.account_id.account_type in ('liability_payable',))
            for line in payable_lines:
                # Recorremos conciliaciones (lo que se ha aplicado a la factura)
                partials =line.matched_debit_ids# line.matched_credit_ids#+
                moves+=partials.mapped('debit_move_id.move_id')#partials.mapped('credit_move_id.move_id')+
        return moves

    def get_withholds(self):
        withhols_lines=self.env["account.move.line"].sudo().search([
            ('l10n_ec_withhold_invoice_id','=',self.ids),
            ('move_id.state','=','posted')
        ])
        return withhols_lines.mapped('move_id')

    def actualizar_reembolso(self,payment,map_amounts={}):
        for brw_each in self:
            reembolso_srch=self.env["hr.registro.reembolsos"].sudo().search([
                ('liquidation_move_id','=',brw_each.id)
            ])
            for brw_reembolso in reembolso_srch:
                brw_reembolso.write({
                    "line_pagos_ids":[(5,),
                                      (0,0,{
                                          "payment_id":payment.id,
                                          "fecha_pago":payment.date,
                                          "diario_pago":payment.journal_id.id,
                                          "monto_pago":map_amounts[brw_each]
                                      })  ]  })
                brw_reembolso.test_paid()
            #################################################################
            liquidation_srch = self.env["hr.registro.caja.chica"].sudo().search([
                ('liquidation_move_id', '=', brw_each.id)
            ])
            for brw_liquidation in liquidation_srch:
                brw_liquidation.write({
                    "line_pagos_ids": [(5,),
                                       (0, 0, {
                                           "payment_id": payment.id,
                                           "fecha_pago": payment.date,
                                           "diario_pago": payment.journal_id.id,
                                           "monto_pago": map_amounts[brw_each]
                                       })]})
                brw_liquidation.test_paid()
        return True

    def get_payment_dscr_summary(self):
        import re

        def extraer_codigo_relacionado(texto):
            """
            Extrae el código posterior a 'Assign of:' del texto dado.
            Retorna el código si lo encuentra, de lo contrario retorna False.
            """
            patron = r'Assign of:\s*(\w+/\d{4}/\d+)'
            coincidencia = re.search(patron, texto)
            return coincidencia.group(1) if coincidencia else False

        self.ensure_one()
        if self.move_type=='entry':
            brw_payment = self.payment_id
            if brw_payment:###
                return brw_payment,"%s,%s" % (brw_payment.journal_id.name,brw_payment.ref)
            if self.ref :
                name_payment=extraer_codigo_relacionado(self.ref or '')
                if name_payment:
                    srch = self.env["account.payment"].sudo().search([('company_id', '=', self.company_id.id),
                                                                      ('partner_id', '=', self.partner_id.id),
                                                                      ('name', '=', name_payment),
                                                                      ('state','=','posted')
                                                                      ])
                    if srch:
                        brw_payment = srch[0]
                        purchases_dscr=",".join(brw_payment.payment_purchase_line_ids.mapped('order_id.name'))
                        return brw_payment, "ANTICIPO %s:%s,%s " % (purchases_dscr,brw_payment.journal_id.name,brw_payment.ref)
        return False,"%s,%s" % (self.journal_id.name,self.ref)

    def get_payment_anticipado(self,move_id):
        self._cr.execute("""SELECT
		fact.id as doc_id,
		moveant.id as move_id, 
		p.move_id as payment_move_id,
			ROUND(SUM(aprpg.AMOUNT),2) AS aplicado 
		FROM ACCOUNT_PARTIAL_rECONCILE APR  
		INNER JOIN ACCOUNT_MOVE_LINE AMLD ON AMLD.ID=APR.DEBIT_MOVE_ID 
		INNER JOIN ACCOUNT_MOVE AM ON AM.ID=AMLD.MOVE_ID 
		INNER JOIN account_payment p ON p.move_id=AM.id  
		INNER JOIN ACCOUNT_MOVE_LINE moveantl ON moveantl.ID=APR.CREDIT_MOVE_ID 
		INNER JOIN ACCOUNT_MOVE moveant ON moveant.ID=moveantl.MOVE_ID and 
			coalesce(moveant.prepayment_Assignment,false) 
		INNER JOIN ACCOUNT_MOVE_LINE movepgl ON movepgl.move_id=moveant.id and movepgl.account_id!= moveantl.account_id
		/*hasta aqui relacion con asiento de contrapartida y cyenta a cruzar*/
		inner join ACCOUNT_PARTIAL_rECONCILE aprpg on aprpg.debit_move_id=movepgl.id
		INNER JOIN ACCOUNT_MOVE_LINE facl ON facl.ID=aprpg.credit_move_id 
		INNER JOIN ACCOUNT_MOVE fact ON fact.ID=facl.MOVE_ID 
		WHERE moveant.id=%s 
		GROUP BY fact.id,moveant.id,  p.move_id """,(move_id,))
        result=self._cr.dictfetchone()
        return result