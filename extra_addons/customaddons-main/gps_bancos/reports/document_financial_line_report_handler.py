# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _

from dateutil.relativedelta import relativedelta
from itertools import chain

class DocumentFinancialLineReportHandler(models.AbstractModel):
    _name = 'document.financial.line.report.handler'
    _inherit = 'account.report.custom.handler'

    def _report_custom_engine_emision_aged(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None):
        return self._get_custom_line_values(options, 'emision', current_groupby, next_groupby, offset=offset, limit=limit)

    def _report_custom_engine_prestamo_aged(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None):
        return self._get_custom_line_values(options, 'prestamo', current_groupby, next_groupby, offset=offset, limit=limit)

    def _report_custom_engine_aged(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None):
        total_documentos= self._get_custom_line_values(options, 'total', current_groupby, next_groupby, offset=offset, limit=limit)
        total_cxp=self._report_custom_engine_cxp_aged(None,options, 'total', current_groupby, next_groupby, offset=offset, limit=limit)
        campos_a_sumar = ['period0', 'period1', 'period2', 'period3', 'period4', 'period5', 'total']

        for campo in campos_a_sumar:
            valor_doc = total_documentos.get(campo) or 0
            valor_cxp = total_cxp.get(campo) or 0
            total_documentos[campo] = valor_doc + valor_cxp

        return total_documentos

    def _report_custom_engine_cxp_aged(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0,
                                        limit=None):
        internal_type='liability_payable'
        report = self.env['account.report'].browse(options['report_id'])
        report._check_groupby_fields(
            (next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        def minus_days(date_obj, days):
            return fields.Date.to_string(date_obj - relativedelta(days=days))

        date_to = fields.Date.from_string(options['date']['date_to'])
        periods = [
            (False, fields.Date.to_string(date_to)),
            (minus_days(date_to, 1), minus_days(date_to, 30)),
            (minus_days(date_to, 31), minus_days(date_to, 60)),
            (minus_days(date_to, 61), minus_days(date_to, 90)),
            (minus_days(date_to, 91), minus_days(date_to, 120)),
            (minus_days(date_to, 121), False),
        ]

        def build_result_dict(report, query_res_lines):
            rslt = {f'period{i}': 0 for i in range(len(periods))}

            for query_res in query_res_lines:
                for i in range(len(periods)):
                    period_key = f'period{i}'
                    rslt[period_key] += query_res[period_key]

            if current_groupby == 'id':
                query_res = query_res_lines[
                    0]  # We're grouping by id, so there is only 1 element in query_res_lines anyway
                currency = self.env['res.currency'].browse(query_res['currency_id'][0]) if len(
                    query_res['currency_id']) == 1 else None
                rslt.update({
                    'date_due': query_res['date_due'][0] if len(query_res['date_due']) == 1 else None,
                    #'amount_currency': report.format_value(query_res['amount_currency'], currency=currency),
                    #'currency': currency.display_name if currency else None,
                    #'account_name': query_res['account_name'][0] if len(query_res['account_name']) == 1 else None,
                    #'expected_date': query_res['expected_date'][0] if len(query_res['expected_date']) == 1 else None,
                    'total': None,
                    'quota':0,
                    'has_sublines': query_res['aml_count'] > 0,
                    #'report_date': query_res['report_date'][0] if len(query_res['report_date']) == 1 else None,
                    # Needed by the custom_unfold_all_batch_data_generator, to speed-up unfold_all
                    'partner_id': query_res['partner_id'][0] if query_res['partner_id'] else None,
                })
            else:
                rslt.update({
                    'date_due': None,
                    'quota':0,
                    #'amount_currency': None,
                    #'currency': None,
                    #'account_name': None,
                    #'expected_date': None,
                    #'report_date': None,
                    'total': sum(rslt[f'period{i}'] for i in range(len(periods))),
                    'has_sublines': False,
                })

            return rslt

        # Build period table
        period_table_format = ('(VALUES %s)' % ','.join("(%s, %s, %s)" for period in periods))
        params = list(chain.from_iterable(
            (period[0] or None, period[1] or None, i)
            for i, period in enumerate(periods)
        ))
        period_table = self.env.cr.mogrify(period_table_format, params).decode(self.env.cr.connection.encoding)
        print(period_table)
        # Build query
        tables, where_clause, where_params = report._query_get(options, 'strict_range',
                                                               domain=[('account_id.account_type', '=', internal_type)])
        print('---------------------------------')
        print(tables)
        print(where_clause)
        print(where_params)
        currency_table = self.env['res.currency']._get_query_currency_table(options)
        always_present_groupby = "period_table.period_index, currency_table.rate, currency_table.precision"

        if current_groupby:
            select_from_groupby = f"account_move_line.{current_groupby} AS grouping_key,"
            groupby_clause = f"account_move_line.{current_groupby}, {always_present_groupby}"
        else:
            select_from_groupby = ''
            groupby_clause = always_present_groupby
        select_period_query = ','.join(
            f"""
                        CASE WHEN period_table.period_index = {i}
                        THEN %s * (
                            SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision))
                            - COALESCE(SUM(ROUND(part_debit.amount * currency_table.rate, currency_table.precision)), 0)
                            + COALESCE(SUM(ROUND(part_credit.amount * currency_table.rate, currency_table.precision)), 0)
                        )
                        ELSE 0 END AS period{i}
                    """
            for i in range(len(periods))
        )

        tail_query, tail_params = report._get_engine_query_tail(offset, limit)
        query = f"""
                    WITH period_table(date_start, date_stop, period_index) AS ({period_table})

                    SELECT
                        {select_from_groupby}
                        %s * SUM(account_move_line.amount_residual_currency) AS amount_currency,
                        ARRAY_AGG(DISTINCT account_move_line.partner_id) AS partner_id,
                        ARRAY_AGG(account_move_line.payment_id) AS payment_id,
                        ARRAY_AGG(DISTINCT COALESCE(account_move_line.date, account_move_line.date)) AS report_date,
                        ARRAY_AGG(DISTINCT account_move_line.expected_pay_date) AS expected_date,
                        ARRAY_AGG(DISTINCT account.code) AS account_name,
                        ARRAY_AGG(DISTINCT COALESCE(account_move_line.date_maturity, account_move_line.date)) AS date_due,
                        ARRAY_AGG(DISTINCT account_move_line.currency_id) AS currency_id,
                        COUNT(account_move_line.id) AS aml_count,
                        ARRAY_AGG(account.code) AS account_code,
                        {select_period_query}

                    FROM {tables}

                    JOIN account_journal journal ON journal.id = account_move_line.journal_id
                    JOIN account_account account ON account.id = account_move_line.account_id
                    JOIN {currency_table} ON currency_table.company_id = account_move_line.company_id

                    LEFT JOIN LATERAL (
                        SELECT SUM(part.amount) AS amount, part.debit_move_id
                        FROM account_partial_reconcile part
                        WHERE part.max_date <= %s
                        GROUP BY part.debit_move_id
                    ) part_debit ON part_debit.debit_move_id = account_move_line.id

                    LEFT JOIN LATERAL (
                        SELECT SUM(part.amount) AS amount, part.credit_move_id
                        FROM account_partial_reconcile part
                        WHERE part.max_date <= %s
                        GROUP BY part.credit_move_id
                    ) part_credit ON part_credit.credit_move_id = account_move_line.id

                    JOIN period_table ON
                        (
                            period_table.date_start IS NULL
                            OR COALESCE(account_move_line.date_maturity, account_move_line.date) <= DATE(period_table.date_start)
                        )
                        AND
                        (
                            period_table.date_stop IS NULL
                            OR COALESCE(account_move_line.date_maturity, account_move_line.date) >= DATE(period_table.date_stop)
                        )

                    WHERE {where_clause}

                    GROUP BY {groupby_clause}

                    HAVING
                        (
                            SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))
                            - COALESCE(SUM(ROUND(part_debit.amount * currency_table.rate, currency_table.precision)), 0)
                        ) != 0
                        OR
                        (
                            SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))
                            - COALESCE(SUM(ROUND(part_credit.amount * currency_table.rate, currency_table.precision)), 0)
                        ) != 0
                    {tail_query}
                """

        multiplicator = -1 if internal_type == 'liability_payable' else 1
        params = [
            multiplicator,
            *([multiplicator] * len(periods)),
            date_to,
            date_to,
            *where_params,
            *tail_params,
        ]
        self._cr.execute(query, params)
        query_res_lines = self._cr.dictfetchall()

        if not current_groupby:
            x = build_result_dict(report, query_res_lines)
            print(1)
            print(x)
            return x
        else:
            rslt = []

            all_res_per_grouping_key = {}
            for query_res in query_res_lines:
                grouping_key = query_res['grouping_key']
                all_res_per_grouping_key.setdefault(grouping_key, []).append(query_res)

            for grouping_key, query_res_lines in all_res_per_grouping_key.items():
                rslt.append((grouping_key, build_result_dict(report, query_res_lines)))
            print(2)
            print(rslt)
            return rslt


    def _get_custom_line_values(self, options, internal_type, current_groupby, next_groupby, offset=0, limit=None):
        print(options)
        report = self.env['account.report'].browse(options['report_id'])
        allowed_company_ids=self._context.get('allowed_company_ids',[])

        date_to = fields.Date.from_string(options['date']['date_to'])
        periods = [
            (fields.Date.to_string(date_to - relativedelta(years=10)), fields.Date.to_string(date_to)),
            (fields.Date.to_string(date_to + relativedelta(days=1)),
             fields.Date.to_string(date_to + relativedelta(days=30))),
            (fields.Date.to_string(date_to + relativedelta(days=31)),
             fields.Date.to_string(date_to + relativedelta(days=60))),
            (fields.Date.to_string(date_to + relativedelta(days=61)),
             fields.Date.to_string(date_to + relativedelta(days=90))),
            (fields.Date.to_string(date_to + relativedelta(days=91)),
             fields.Date.to_string(date_to + relativedelta(days=120))),
            (fields.Date.to_string(date_to + relativedelta(days=121)), fields.Date.to_string(date_to + relativedelta(years=50))),
        ]

        def build_result_dict(report,query_res_lines):
            rslt = {f'period{i}': 0 for i in range(len(periods))}
            for query_res in query_res_lines:
                for i in range(len(periods)):
                    rslt[f'period{i}'] += query_res[f'period{i}']
            if current_groupby == 'id':
                query_res = query_res_lines[  0]  # We're grouping by id, so there is only 1 element in query_res_lines anyway
                #currency = self.env['res.currency'].browse(query_res['currency_id'][0]) if len(
                #    query_res['currency_id']) == 1 else None
                brw_financial_line=self.env["document.financial.line"].browse(query_res['grouping_key'])
                rslt.update({
                    'date_due': brw_financial_line.date_process,
                    'has_sublines': query_res['counter'] > 0,
                    'quota':brw_financial_line.quota,
                    'total': sum(query_res[f'period{i}'] for i in range(len(periods))),
                })
            else:
                rslt.update({
                    'total': sum(rslt[f'period{i}'] for i in range(len(periods))),
                    'has_sublines': False,
                    'date_due':None,
                    'quota':0
                })
            return rslt

        # Construir tabla de periodos
        period_table_format = ('(VALUES %s)' % ','.join("(%s, %s, %s)" for _ in periods))
        params = list(chain.from_iterable((p[0] or None, p[1] or None, i) for i, p in enumerate(periods)))
        period_table = self.env.cr.mogrify(period_table_format, params).decode(self.env.cr.connection.encoding)
        #groupby_sql = f'dbkl.{current_groupby}' if current_groupby else None
        #print(groupby_sql)
        #print(next_groupby)
        order_by = ""
        always_present_groupby = "period_table.period_index"
        if current_groupby:
            select_from_groupby = f"dbkl.{current_groupby} AS grouping_key,"
            groupby_clause = f"dbkl.{current_groupby}, {always_present_groupby}"

            order_by += f" dbkl.{current_groupby}"

        else:
            select_from_groupby = ''
            groupby_clause = always_present_groupby

        # Consulta adaptada a document_financial_line
        tail_query, tail_params = report._get_engine_query_tail(offset, limit)


        where_clause=" "

        forced_domain=options["forced_domain"]
        i=0
        for field_name,operator,value in forced_domain:
            where_clause+= f" and dbkl.{field_name} {operator} {value} "
            i+=1

        if len(order_by)>0:
            order_by = " order by "+order_by
        tail_query=order_by+" "+tail_query
        query = f"""
                       WITH period_table(date_start, date_stop, period_index) AS ({period_table})

                       SELECT
                           {select_from_groupby}
                           {', '.join(f"SUM(CASE WHEN period_table.period_index = {i} THEN dbkl.total_pending ELSE 0 END) AS period{i}" for i in range(len(periods)))},
                           count(1) as counter

                       FROM document_financial dbk
                       INNER JOIN document_financial_line dbkl ON dbkl.document_id = dbk.id
                       inner JOIN period_table ON
                           (dbkl.date_process >= period_table.date_start::date)
                           AND
                           ( dbkl.date_process <= period_table.date_stop::date) 
                           
                       WHERE dbk.state = 'posted' and dbk.company_id in {tuple(allowed_company_ids+[-1])}
                         AND dbkl.total_pending != 0.00
                         AND dbk.internal_type = 'out'
                         AND ('{internal_type}'='total' or ('{internal_type}'!='total' and dbk.type = '{internal_type}')) {where_clause}

                       GROUP BY {groupby_clause}
                       
                       HAVING SUM(dbkl.total_pending)>0 
                       
                     {tail_query}
                   """


        self.env.cr.execute(query, params)
        query_res_lines = self.env.cr.dictfetchall()

        if not current_groupby:
            return build_result_dict(report,query_res_lines)
        else:
            rslt = []

            all_res_per_grouping_key = {}
            for query_res in query_res_lines:
                grouping_key = query_res['grouping_key']
                all_res_per_grouping_key.setdefault(grouping_key, []).append(query_res)

            for grouping_key, query_res_lines in all_res_per_grouping_key.items():
                rslt.append((grouping_key, build_result_dict(report, query_res_lines)))
            return rslt


