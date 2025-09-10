# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from ...calendar_days.tools import DateManager

dtObj=DateManager()
from datetime import timedelta

class HrVacationPeriod(models.Model):
    _name = "hr.vacation.period"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Periodo de vacaciones"


    @api.onchange('year_start','year_end','contract_id')
    @api.depends('year_start', 'year_end','contract_id')
    def _compute_control_datas(self):
        for brw_each in self:
            name = _("PERIODO %s-%s DEL CONTRATO %s") % (brw_each.year_start, brw_each.year_end, brw_each.contract_id.name)
            brw_each.name = name
            request_ids=brw_each.line_ids.mapped('request_id').filtered(lambda x: x.state!='refuse')
            brw_each.request_ids=request_ids
            brw_each.request_counter = len(request_ids)


    name = fields.Char(compute="_compute_control_datas", string="Descripción")
    process_counter = fields.Integer(compute="_compute_control_datas", string="# Procesos")
    comments = fields.Text("Comentarios",tracking=True)
    contract_id = fields.Many2one("hr.contract", "Contrato", required=True,tracking=True)
    employee_id = fields.Many2one("hr.employee", "Empleado", required=True  ,tracking=True)
    company_id = fields.Many2one("res.company", "Empresa", required=True,tracking=True)
    date_start = fields.Date("Fecha Inicio", required=True,tracking=True)
    date_end = fields.Date("Fecha Fin", required=True,tracking=True)
    year_start = fields.Integer("Año Inicial", required=True,tracking=True)
    year_end = fields.Integer("Año Final", required=True,tracking=True)
    date_start_contract = fields.Date("Fecha Inicial Contrato",tracking=True)
    date_end_contract = fields.Date("Fecha Final Contrato",tracking=True)
    year_start_contract = fields.Integer("Año Contrato", required=True)
    month_start_contract = fields.Integer("Mes Contrato", required=True)
    day_start_contract = fields.Integer("Dia Contrato", required=True)
    add_year_days = fields.Integer("Dias Adicionales", required=True)
    years = fields.Integer("Año(s)", required=True)
    attempt_days = fields.Integer("Dias Tentativos", required=True, default=0,tracking=True)
    days = fields.Integer("Dia(s)", required=True, default=0,tracking=True)
    period_days = fields.Integer("Dias del Periodo", required=True, default=0)
    passed_days = fields.Integer("Dias Transcurridos", required=True, default=0)
    migrated = fields.Boolean("Migrado", default=True)
    weekend_days = fields.Integer("Dias(Fines de Semana)", required=True, default=0, help="Dias de fines de semanas ya utilizados. No pueden ser mayor a 4 (2 fines de semanas)",compute="_get_compute_pending_days")

    pending_days = fields.Integer("Pendiente(s)", default=0,compute="_get_compute_pending_days",store= True,readonly=True,tracking=True)
    attempt_pending_days = fields.Integer("P. Tentativos(s)", default=0,compute="_get_compute_pending_days",store= True,readonly=True,tracking=True)
    taken_days = fields.Integer("Utilizado(s)", default=0,compute="_get_compute_pending_days",store= True,readonly=True ,tracking=True)
    taken_pending_migrated_days = fields.Integer("U. Previamente", required=True, default=0,
                                                 help="Dia(s) Utilizado(s) antes del Sistema",tracking=True)
    total_taken_days = fields.Integer(compute="_get_compute_pending_days", string="Total Utilizados",store= True,readonly=True,tracking=True )

    locked = fields.Boolean("Bloqueado", help="Finalizado de actualizar los dias ganados", default=False)

    state = fields.Selection([
        ('draft', 'Preliminar'),
        ('confirmed', 'Confirmado'),
        ('ended', 'Finalizado')
    ], string="Estado", default="draft",tracking=True)
    request_ids = fields.Many2many("hr.leave", "vacation_period_leave_rel", "period_id", "leave_id", "Solicitud(es)", compute="_compute_control_datas")
    request_counter = fields.Integer("# Solicitud(es)", compute="_compute_control_datas")
    line_ids = fields.One2many("hr.vacation.period.line", "period_id", "Detalle")

    _rec_name = "name"
    _order = "year_start, year_end desc"

    _sql_constraints = [
        ("hr_period_vacation_unique_period", "unique(contract_id,year_start,year_end)", "Periodo de Vacaciones debe ser único por contrato")
    ]

    @api.depends('line_ids',
                 'line_ids.days','line_ids.date_start','line_ids.date_stop',
                 'line_ids.request_id.state',
                 'attempt_days','days','state','taken_pending_migrated_days',
                 'request_ids','request_ids.request_date_from','request_ids.request_date_to'
                 )
    @api.onchange('line_ids',
                 'line_ids.days', 'line_ids.date_start', 'line_ids.date_stop','line_ids.type','line_ids.payment_state',
                 'line_ids.request_id.state',
                 'attempt_days', 'days', 'state', 'taken_pending_migrated_days',
                  'request_ids','request_ids.request_date_from','request_ids.request_date_to')
    def _get_compute_pending_days(self):
        for brw_each in self:
            for_vacations_request = 0
            weekends_count = 0
            for brw_line in brw_each.line_ids:
                if brw_line.state not in ('refuse','cancel') and brw_line.days>0:
                    if brw_line.type=='request':
                        if brw_line.date_start and brw_line.date_stop:
                            # Contar días solicitados
                            for_vacations_request += brw_line.days

                            # Contar sábados y domingos entre start y stop
                            date = brw_line.date_start
                            while date <= brw_line.date_stop:
                                if date.weekday() in (5, 6):  # 5 = sábado, 6 = domingo
                                    weekends_count += 1
                                date += timedelta(days=1)
                    else:
                        for_vacations_request += brw_line.days

            #taken_days = brw_each.taken_pending_migrated_days
            total_taken_days = for_vacations_request #+ taken_days
            brw_each.taken_days = for_vacations_request
            brw_each.total_taken_days = total_taken_days
            brw_each.pending_days = brw_each.days - total_taken_days
            brw_each.attempt_pending_days = brw_each.attempt_days - total_taken_days

            # Puedes guardar los fines de semana si deseas en otro campo:
            brw_each.weekend_days = weekends_count  # Asegúrate de tener este campo definido si lo usas

            brw_each.test_period()

    @api.constrains('weekend_days')
    def validate_weekend_days(self):
        for brw_each in self:
            if brw_each.attempt_days <= 15:
                max_weekends = 5
            else:
                # proporcional: 4 fines de semana por 15 días, entonces 8 por 30
                max_weekends = round((brw_each.attempt_pending_days / 15.0) * 4)
                if max_weekends==5:
                    max_weekends=6
                if max_weekends==7:
                    max_weekends=8
                if max_weekends==9:
                    max_weekends=8
            if brw_each.weekend_days > max_weekends:
                #pass
                raise ValidationError(
                    _("Los fines de semana tomados (%s) no pueden ser mayores a %s según su antigüedad.")
                    % (brw_each.weekend_days, max_weekends)
                )
    @api.model
    def create(self, vals):
        brw_new = super(HrVacationPeriod, self).create(vals)
        # self.env["hr.vacation.period.history"].register(brw_new.id, _("REGISTRO CREADO"), brw_new.state)
        brw_new.validate_period()
        return brw_new

    def write(self, vals):
        value = super(HrVacationPeriod, self).write(vals)
        for brw_each in self:
            brw_each.update_taken_pending_migrated_days()
            brw_each.validate_period()
            brw_each.test_period()
        return value

    def action_approved(self):
        for brw_each in self:
            brw_each.update_workflow("ACTUALIZADO","confirmed")
        return True


    def update_taken_pending_migrated_days(self):
        for brw_each in self:
            taken_pending_migrated_days=brw_each.taken_pending_migrated_days
            srch_lines=self.env["hr.vacation.period.line"].sudo().search([('period_id','=',brw_each.id),
                                                                          ('type','=','migrated')
                                                                          ])
            if not srch_lines:
                self.env["hr.vacation.period.line"].create({
                    'period_id': brw_each.id,
                    'type':'migrated',
                    'days':taken_pending_migrated_days,
                    "name":"DIAS UTILIZADOS PREVIAMENTE",
                    "comments":"DIAS QUE FUERON UTILIZADOS PREVIO AL USO DEL SISTEMA"
                })
            else:
                srch_lines.write({
                    'days': taken_pending_migrated_days
                })
        return True

    def update_workflow(self, comments, state):
        #OBJ_HISTORY = self.env["hr.vacation.period.history"]
        for brw_each in self:
            last_state = brw_each.state
            if last_state == "draft" and state == "approved" and brw_each.days > 0:
                raise ValidationError(_("Necesitas al menos 1 dia para aprobar este periodo"))
            if last_state == "approved" and state == "ended":
                if brw_each.line_ids:
                    counter_all = sum(
                        1 for brw_line in brw_each.line_ids if brw_line.request_id.state not in ("refuse",))
                    counter_ended = sum(1 for brw_line in brw_each.line_ids if brw_line.request_id.state == "validate")
                    if counter_all != counter_ended:
                        raise ValidationError(_("Deben estar todas las solicitudes de vacaciones finalizadas"))
            brw_each._write({"state": state})
            #OBJ_HISTORY.register(brw_each.id, comments, state)
        return True

    def validate_period(self):
        for brw_each in self:
            if brw_each.state == 'confirmed':
                if not brw_each.date_end_contract:
                    attempt_pending_days=brw_each.taken_pending_migrated_days
                    attempt_pending_days+=sum(brw_each.line_ids.mapped('days'))
                    if attempt_pending_days < 0:
                        raise ValidationError(
                                _("Dias pendientes por solicitar (tentativos) no pueden ser negativos %s ,periodo # %s") % (
                                attempt_pending_days, brw_each.id))
        return True

    def test_period(self):
        for brw_each in self:
            if brw_each.state == "confirmed" and brw_each.days == brw_each.attempt_days:  # confirmado y tomado todos los días hábiles posibles
                OBJ_LINE = self.env["hr.vacation.period.line"]
                line_srch = OBJ_LINE.search([('period_id', '=', brw_each.id), ('request_id.state', '=', 'refuse')])
                if line_srch:
                    line_srch.unlink()

                if not brw_each.date_end_contract:
                    if brw_each.pending_days < 0 or brw_each.attempt_pending_days < 0:
                        raise ValidationError(_("La solicitud de vacaciones de %s supera los días disponibles %s") % (
                        brw_each.employee_id.name, int(brw_each.pending_days)))

                if brw_each.pending_days == 0 and brw_each.attempt_pending_days == 0:
                    if brw_each.line_ids:
                        counter_all = 0
                        counter_ended = 0
                        for brw_line in brw_each.line_ids:
                            if brw_line.type=='request':
                                if brw_line.request_id.state not in ("refuse",):
                                    counter_all += 1
                                if brw_line.request_id.state == "validate":
                                    counter_ended += 1
                        if counter_all == counter_ended:  # solicitudes y solicitudes finalizadas
                            brw_each.update_workflow(_("FINALIZADO"), "ended")
                    else:##no ahy solicitudes todo fue usado desde el cmapo de u previamente o finde smeana
                        brw_each.update_workflow(_("FINALIZADO"), "ended")
        return True

    def synchronize_ended_periods(self):
        for brw_company in self.env["res.company"].sudo().search([]):
            self._cr.execute("""SELECT VP.ID,VP.PENDING_DAYS FROM HR_VACATION_PERIOD VP
    WHERE VP.STATE='confirmed' AND VP.ATTEMPT_DAYS=VP.DAYS
    AND VP.ATTEMPT_PENDING_DAYS=VP.PENDING_DAYS
    AND VP.PENDING_DAYS=0 AND VP.COMPANY_ID=%s""", (brw_company.id,))
            result = self._cr.fetchall()
            for period_id, pending_days in result:
                brw_period = self.browse(period_id)
                brw_period.test_period()
        return True

    def synchronize_periods(self, contract_id=0):
        # Obteniendo las compañías

        ##########################################################################
        self._cr.execute("""update 
        hr_vacation_period
        set company_id=x.company_id
        from (
        	select vp.id,hc.company_id
        	from 
        	hr_vacation_period vp
        	inner join hr_contract hc on hc.id=vp.contract_id
        	where  vp.state in ('draft','confirmed')
        	and hc.company_id!=vp.company_id  

        ) x
        where hr_vacation_period.id=x.id   """)
        ##########################################################################

        self._cr.execute("""SELECT RC.ID, RC.NAME
                                                  FROM RES_COMPANY RC
                                                  ORDER BY RC.ID ASC""")
        company_result = self._cr.fetchall()
        if company_result:
            for company_id, DB in company_result:

                nowDate = fields.Date.context_today(self)
                start_year = nowDate.year
                end_year = nowDate.year + 1

                # Obteniendo empleados para el año correspondiente
                self._cr.execute("""SELECT HE.ID, HE.NAME AS NAME_RELATED 
                                                       FROM HR_EMPLOYEE HE
                                                       INNER JOIN HR_CONTRACT HC ON HC.EMPLOYEE_ID=HE.ID 
                                                       INNER JOIN HR_CONTRACT_TYPE HCT ON HCT.ID=HC.CONTRACT_TYPE_id  
                                                       LEFT JOIN HR_VACATION_PERIOD VP ON VP.CONTRACT_ID=HC.ID 
                                                       AND VP.YEAR_START=%s AND VP.YEAR_END=%s
                                                       WHERE HC.STATE='open' 
                                                       AND (%s >= EXTRACT(YEAR FROM (HC.DATE_START)) 
                                                       AND EXTRACT(YEAR FROM (HC.DATE_START)) <= %s)
                                                       AND COALESCE(VP.LOCKED, FALSE) = FALSE 
                                                       AND (HC.ID = %s OR %s = 0) 
                                                       AND HC.COMPANY_ID = %s and hct.legal_iess  
                                                       ORDER BY HE.NAME  ASC""",
                                 (start_year, end_year, start_year, end_year, contract_id, contract_id, company_id))
                employee_list_ids = self._cr.fetchall()#

                employee_list_ids = employee_list_ids and [*dict(employee_list_ids)] or []
                print(employee_list_ids)
                self.create_periods(company_id, start_year, end_year, employee_ids=employee_list_ids)

                # Actualizar periodos activos anteriores
                self._cr.execute("""SELECT VP.YEAR_START, VP.YEAR_END 
                                       FROM HR_EMPLOYEE HE
                                       INNER JOIN HR_CONTRACT HC ON HC.EMPLOYEE_ID=HE.ID 
                                       INNER JOIN HR_CONTRACT_TYPE HCT ON HCT.ID=HC.CONTRACT_TYPE_id  
                                       
                                       INNER JOIN HR_VACATION_PERIOD VP ON VP.CONTRACT_ID=HC.ID 
                                       AND COALESCE(VP.LOCKED, FALSE) = FALSE 
                                       AND VP.STATE != 'ended' 
                                       AND VP.YEAR_START != %s AND VP.YEAR_END != %s 
                                       AND (VP.CONTRACT_ID = %s OR %s = 0) 
                                       AND HC.COMPANY_ID = %s  and hct.legal_iess   
                                       GROUP BY VP.YEAR_START, VP.YEAR_END """,
                                    (start_year, end_year, contract_id, contract_id, company_id))#

                result = self._cr.fetchall()
                print(result)
                if result:
                    for old_start_year, old_end_year in result:
                        self._cr.execute("""SELECT VP.EMPLOYEE_ID, VP.EMPLOYEE_ID
                                               FROM HR_VACATION_PERIOD VP
                                               WHERE VP.YEAR_START = %s AND VP.YEAR_END = %s 
                                               AND COALESCE(VP.LOCKED, FALSE) = FALSE 
                                               AND (VP.CONTRACT_ID = %s OR %s = 0)  
                                               AND VP.COMPANY_ID = %s  
                                               ORDER BY VP.EMPLOYEE_ID ASC""",
                                            (old_start_year, old_end_year, contract_id, contract_id, company_id))
                        employee_list_ids = self.env.cr.fetchall()
                        if employee_list_ids:
                            employee_list_ids =[* dict(employee_list_ids) ]
                            self.create_periods(company_id, old_start_year, old_end_year, employee_ids = employee_list_ids)

                            # Actualizar periodos de empleados inactivos
                self._cr.execute("""SELECT VP.ID, VP.STATE, HC.date_end as SETTLEMENT_DATE 
                                       FROM HR_VACATION_PERIOD VP 
                                       INNER JOIN HR_CONTRACT HC ON HC.ID=VP.CONTRACT_ID
                                       WHERE COALESCE(VP.LOCKED, FALSE) = FALSE  
                                       AND HC.STATE='ended' 
                                       AND (VP.CONTRACT_ID = %s OR %s = 0) 
                                       AND VP.COMPANY_ID = %s  
                                       ORDER BY VP.EMPLOYEE_ID ASC""",
                                    (contract_id, contract_id, company_id))
                result = self._cr.fetchall()

                if result:
                    for period_id, state, settlement_date in result:
                        brw_period = self.browse(period_id)
                        brw_period.write({"date_end_contract": settlement_date})
                        brw_period.update_workflow(_("FINALIZACION DE CONTRATO"), brw_period.state)
                        if brw_period.state in ("draft",):
                            brw_period.update_workflow(_("FINALIZACION DE CONTRATO"), "confirmed")

                        self._cr.execute("""SELECT (P.DATE_END - P.DATE_START) AS PERIOD_DAYS,
                                                       (P.DATE_END_CONTRACT - P.DATE_START) AS PASSED_DAYS,
                                                       ((15 + P.ADD_YEAR_DAYS)::FLOAT * 
                                                       (CASE WHEN ((P.DATE_END_CONTRACT - P.DATE_START)::FLOAT) <= 0 
                                                             THEN 0 
                                                             ELSE ((P.DATE_END_CONTRACT - P.DATE_START)::FLOAT / 
                                                                   (P.DATE_END - P.DATE_START)::FLOAT) END)::FLOAT)::INT AS ATTEMPT_DAYS
                                               FROM HR_VACATION_PERIOD P
                                               WHERE P.ID = %s AND P.DATE_END_CONTRACT IS NOT NULL 
                                               ORDER BY P.DATE_START ASC""",
                                            (period_id,))
                        result = self._cr.fetchall()

                        if result:
                            for period_days, passed_days, attempt_days in result:
                                days = attempt_days
                                brw_period.write({
                                    "attempt_days": attempt_days,
                                    "passed_days": passed_days,
                                    "period_days": period_days,
                                    "days": days,
                                    "locked": (int(attempt_days) == int(days))
                                })
                                brw_period.validate_period()
                                brw_period.test_period()

        return True

    def create_periods(self, company_id, start_year, end_year, employee_ids=[]):
        employee_list_ids = employee_ids[:]
        if not employee_list_ids:
            self.env.cr.execute("""SELECT HE.ID, HE.NAME AS NAME_RELATED 
                                               FROM HR_EMPLOYEE HE
                                               INNER JOIN HR_CONTRACT HC ON HC.EMPLOYEE_ID = HE.ID 
                                               INNER JOIN HR_CONTRACT_TYPE HCT ON HCT.ID=HC.CONTRACT_TYPE_id  
                                               LEFT JOIN HR_VACATION_PERIOD VP ON VP.CONTRACT_ID = HC.ID 
                                               AND VP.YEAR_START = %s AND VP.YEAR_END = %s
                                               WHERE HC.STATE='open'
                                               AND (%s >= EXTRACT(YEAR FROM (HC.DATE_START)) 
                                               AND EXTRACT(YEAR FROM (HC.DATE_START)) <= %s)
                                               AND COALESCE(VP.LOCKED, FALSE) = FALSE 
                                               and hct.legal_iess  
                                               ORDER BY HE.NAME ASC""",
                                (start_year, end_year, start_year, end_year))
            employee_list_ids = self.env.cr.fetchall()
            employee_list_ids = [*dict(employee_list_ids)]

        employee_list_ids+=[-1]

        self.env.cr.execute("""WITH VARIABLES AS (SELECT 
                                                     %s AS COMPANY_ID,
                                                     NOW()::DATE AS TODAY,
                                                     %s AS START_YEAR,
                                                     %s AS END_YEAR
                                                   ),
                                                   YEAR_PERIOD AS (SELECT 
                                                     HE.ID AS EMPLOYEE_ID,
                                                     HC.ID AS CONTRACT_ID,
                                                     HC.COMPANY_ID,
                                                     HC.DATE_START,
                                                     HC.DATE_END,
                                                     EXTRACT(DAY FROM HC.DATE_START)::INT AS START_PERIOD_DAY,
                                                     EXTRACT(MONTH FROM HC.DATE_START)::INT AS START_PERIOD_MONTH,
                                                     EXTRACT(YEAR FROM HC.DATE_START)::INT AS START_PERIOD_YEAR,
                                                     GENERATE_SERIES(EXTRACT(YEAR FROM HC.DATE_START)::INT, VARIABLES.END_YEAR) AS YEAR
                                                   FROM HR_CONTRACT HC 
                                                   INNER JOIN HR_CONTRACT_TYPE HCT ON HCT.ID=HC.CONTRACT_TYPE_id   
                                                   INNER JOIN HR_EMPLOYEE HE ON HE.ID = HC.EMPLOYEE_ID
                                                   INNER JOIN VARIABLES ON 1 = 1
                                                   WHERE HC.STATE!='ended'
                                                   AND HC.COMPANY_ID = VARIABLES.COMPANY_ID 
                                                   AND HE.ID IN %s and hct.legal_iess   
                                                  ),
                                                   TRANSACTION_PERIOD_TEMP AS (
                                                     SELECT P.*, 
                                                            (P.YEAR - 1) AS LAST_YEAR,
                                                            (VARIABLES.END_YEAR - P.START_PERIOD_YEAR) AS YEARS,
                                                            (CASE WHEN ((VARIABLES.END_YEAR - P.START_PERIOD_YEAR) > 5) 
                                                                  THEN ((VARIABLES.END_YEAR - P.START_PERIOD_YEAR) - 5) ELSE 0 END) AS ADD_YEARS
                                                     FROM YEAR_PERIOD P
                                                     INNER JOIN VARIABLES ON 1 = 1
                                                     WHERE (P.YEAR - 1) >= VARIABLES.START_YEAR 
                                                       AND P.YEAR <= VARIABLES.END_YEAR
                                                   ),
                                                   PERIOD_VACATION AS (
                                                     SELECT T.COMPANY_ID,
                                                            T.CONTRACT_ID,
                                                            T.EMPLOYEE_ID,
                                                            T.DATE_START AS DATE_START_CONTRACT,
                                                            T.DATE_END AS DATE_END_CONTRACT,
                                                            T.START_PERIOD_DAY AS DAY_START_CONTRACT,
                                                            T.START_PERIOD_MONTH AS MONTH_START_CONTRACT,
                                                            T.START_PERIOD_YEAR AS YEAR_START_CONTRACT,
                                                            T.LAST_YEAR AS YEAR_START,
                                                            T.YEAR AS YEAR_END,
                                                            T.YEARS,
                                                            T.ADD_YEARS,
                                                            (CASE WHEN ((15 + T.ADD_YEARS) < 30) THEN 15 + T.ADD_YEARS ELSE 30 END) AS ATTEMPT_DAYS,
                                                            (T.DATE_START + ((CAST((T.YEARS - 1) AS VARCHAR) || ' YEAR')::INTERVAL))::DATE AS DATE_START,
                                                            ((T.DATE_START + ((CAST(T.YEARS AS VARCHAR) || ' YEAR')::INTERVAL)) - INTERVAL '1 DAY')::DATE AS DATE_END
                                                     FROM TRANSACTION_PERIOD_TEMP T
                                                     INNER JOIN VARIABLES ON 1 = 1
                                                     INNER JOIN HR_CONTRACT HC ON HC.ID = T.CONTRACT_ID
                                                     WHERE VARIABLES.START_YEAR >= T.START_PERIOD_YEAR 
                                                       AND HC.STATE='open'
                                                   )
                                                   SELECT P.*,
                                                          (P.DATE_END - P.DATE_START) AS PERIOD_DAYS,
                                                          (CASE WHEN (VARIABLES.TODAY >= P.DATE_END) 
                                                                THEN P.DATE_END - P.DATE_START 
                                                                ELSE VARIABLES.TODAY - P.DATE_START END) AS PASSED_DAYS,
                                                          ((P.ATTEMPT_DAYS *
                                                            ((CASE WHEN (VARIABLES.TODAY >= P.DATE_END) 
                                                                  THEN P.DATE_END - P.DATE_START 
                                                                  ELSE VARIABLES.TODAY - P.DATE_START END)::FLOAT / 
                                                            (P.DATE_END - P.DATE_START)::FLOAT))::INT) AS DAYS
                                                   FROM PERIOD_VACATION P
                                                   INNER JOIN VARIABLES ON 1 = 1
                                                   ORDER BY P.DATE_START ASC""",
                            (company_id, start_year, end_year, tuple(employee_list_ids)))

        result = self._cr.fetchall()
        #print("--",result)
        if result:

            for company_id, contract_id, employee_id, date_start_contract, date_end_contract, day_start_contract, month_start_contract, year_start_contract, year_start, year_end, years, add_year_days, attempt_days, date_start, date_end, period_days, passed_days, days in result:
                brw_company = self.env["res.company"].browse(company_id)

                days = (days > 0) and days or 0
                #print("xxxxxxxx",days)
                if days >= 0:

                    srch_periods = self.search([('year_start', '=', year_start),
                                                ('year_end', '=', year_end),
                                                ('company_id', '=', company_id),
                                                ('contract_id', '=', contract_id)])
                    if not srch_periods:
                        brw_create = self.create({
                            "company_id": company_id,
                            "contract_id": contract_id,
                            "employee_id": employee_id,
                            "date_start_contract": date_start_contract,
                            "date_end_contract": date_end_contract,
                            "day_start_contract": day_start_contract,
                            "month_start_contract": month_start_contract,
                            "year_start_contract": year_start_contract,
                            "year_start": year_start,
                            "year_end": year_end,
                            "years": years,
                            "add_year_days": add_year_days,
                            "attempt_days": attempt_days,
                            "date_start": date_start,
                            "date_end": date_end,
                            "passed_days": passed_days,
                            "period_days": period_days,
                            "days": days,
                            "state": "draft",
                            "locked": (int(attempt_days) == int(days))
                        })
                        if brw_create.passed_days >= brw_company.vacation_passed_days:
                            brw_create.update_workflow(_("PERIODO DE VACACIONES CONFIRMADO"), "confirmed")
                        srch_periods = brw_create
                    else:
                        srch_periods.write({
                            "date_start": date_start,
                            "date_end": date_end,
                            "attempt_days": attempt_days,
                            "passed_days": passed_days,
                            "period_days": period_days,
                            "days": days,
                            "locked": (int(attempt_days) == int(days))
                        })
                        for brw_period in srch_periods:
                            if brw_period.state == "draft" and brw_period.passed_days >= brw_company.vacation_passed_days:
                                brw_period.update_workflow(_("PERIODO DE VACACIONES CONFIRMADO"), "confirmed")
        return True