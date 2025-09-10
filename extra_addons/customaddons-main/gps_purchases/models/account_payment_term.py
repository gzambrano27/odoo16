# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    required_advance_payment=fields.Boolean(string="Requiere Anticipo",default=False)

    def get_payment_term_values(self):
        self.ensure_one()
        self._cr.execute("""SELECT 
		ROW_NUMBER() OVER (PARTITION BY APT.ID ORDER BY CASE 
	        WHEN (COALESCE(APTL.DAYS, 0) > 0) THEN (COALESCE(APTL.DAYS, 0) || ' days') 
	        WHEN (COALESCE(APTL.MONTHS, 0) > 0) THEN (COALESCE(APTL.MONTHS, 0) || ' months') 
	        ELSE '0 days'
	    END::INTERVAL ) as index  ,
	    APT.ID,
	    COALESCE(APTL.MONTHS, 0) AS MONTHS,
	    COALESCE(APTL.DAYS, 0) AS DAYS,
	    APTL.VALUE,
	    case when (APTL.VALUE='balance') then 0 else APTL.VALUE_AMOUNT end as VALUE_AMOUNT ,
	    CASE 
	        WHEN (COALESCE(APTL.DAYS, 0) > 0) THEN (COALESCE(APTL.DAYS, 0) || ' days') 
	        WHEN (COALESCE(APTL.MONTHS, 0) > 0) THEN (COALESCE(APTL.MONTHS, 0) || ' months') 
	        ELSE '0 days'
	    END::INTERVAL AS interval_time   ,
		round((case when (APTL.VALUE='balance') then 100.00- (
			SUM(case when (APTL.VALUE='balance') then 0 else APTL.VALUE_AMOUNT end ) OVER (PARTITION BY APT.ID ORDER BY CASE 
	        WHEN (COALESCE(APTL.DAYS, 0) > 0) THEN (COALESCE(APTL.DAYS, 0) || ' days') 
	        WHEN (COALESCE(APTL.MONTHS, 0) > 0) THEN (COALESCE(APTL.MONTHS, 0) || ' months') 
	        ELSE '0 days'
	    	END::INTERVAL)-(case when (APTL.VALUE='balance') then 0 else APTL.VALUE_AMOUNT end)
		) else APTL.VALUE_AMOUNT end),2)	 as final_amount
		FROM 
		    ACCOUNT_PAYMENT_TERM APT
		INNER JOIN 
		    ACCOUNT_PAYMENT_TERM_LINE APTL 
		    ON APTL.PAYMENT_ID = APT.ID 
		WHERE APT.ID=%s """,(self.id,))
        result=self._cr.dictfetchone()

        return result