from odoo import fields, models, api


class EmployeeAttendanceCalendar(models.Model):
	_name = "employee.attendance.calendar"
	_description = "Asistencia de empleados por calendario"
	_auto = False  # importante: no crea tabla, usa la vista

	id = fields.Integer(string="ID", readonly=True)
	empleado_id = fields.Many2one("hr.employee", string="Empleado", readonly=True)
	empleado_nombre = fields.Char(string="Nombre Empleado", readonly=True)
	fecha = fields.Date(string="Fecha", readonly=True)

	day_id = fields.Many2one("calendar.day", string="Día", readonly=True)
	calendario_id = fields.Many2one("resource.calendar", string="Calendario", readonly=True)
	dia_semana = fields.Integer(string="Día Semana", readonly=True)

	entrada_real = fields.Datetime(string="Entrada", readonly=True)
	salida_real = fields.Datetime(string="Salida", readonly=True)

	entrada_hora = fields.Float(string="Hora Entrada", readonly=True)
	salida_hora = fields.Float(string="Hora Salida", readonly=True)

	inicio = fields.Float(string="Inicio Jornada", readonly=True)
	# fin_medio = fields.Float(string="Fin Medio Día", readonly=True)
	# inicio_medio = fields.Float(string="Inicio Medio Día", readonly=True)
	fin = fields.Float(string="Fin Jornada", readonly=True)

	estado_marcacion = fields.Selection([
		('completo', 'Completo'),
		('incompleto', 'Incompleto'),
	], string="Estado Marcación", readonly=True)

	dif_min_entrada = fields.Integer(string="Dif. Min Ent.", readonly=True)
	estado_entrada = fields.Selection([
		('sin_horario', 'Sin Horario'),
		('temprano', 'Temprano'),
		('puntual', 'Puntual'),
		('atraso', 'Atraso'),
	], string="Estado Entrada", readonly=True)

	dif_min_salida = fields.Integer(string="Dif. Min Sal.", readonly=True)
	estado_salida = fields.Selection([
		('sin_horario', 'Sin Horario'),
		('anticipada', 'Anticipada'),
		('puntual', 'Puntual'),
		('tardia', 'Tardía'),
	], string="Estado Salida", readonly=True)

	minutos_descontar = fields.Integer("Min. Descontar", default=0)
	minutos_extras = fields.Integer("Min. Extras", default=0)

	feriado_id = fields.Many2one('calendar.holiday', 'Feriado')

	def init(self):
		"""Inicializa la vista en PostgreSQL"""
		self.env.cr.execute(""" 
            
CREATE OR REPLACE VIEW employee_attendance_calendar AS



WITH
-- 1) Todo a hora local una sola vez
limites AS (
    SELECT
        MIN((ear.date_time AT TIME ZONE 'UTC' AT TIME ZONE 'America/Guayaquil')::date) AS fecha_min,
        MAX((ear.date_time AT TIME ZONE 'UTC' AT TIME ZONE 'America/Guayaquil')::date) AS fecha_max
    FROM employee_attendance_raw ear
),

marcaciones AS (
    SELECT
        ear.employee_id,
        (ear.date_time AT TIME ZONE 'UTC' AT TIME ZONE 'America/Guayaquil')::date AS fecha,
        MIN(ear.date_time AT TIME ZONE 'UTC' AT TIME ZONE 'America/Guayaquil') AS entrada_real,
        CASE
            WHEN MIN(ear.date_time) <> MAX(ear.date_time)
            THEN MAX(ear.date_time AT TIME ZONE 'UTC' AT TIME ZONE 'America/Guayaquil')
            ELSE NULL
        END AS salida_real
    FROM employee_attendance_raw ear
    GROUP BY ear.employee_id, (ear.date_time AT TIME ZONE 'UTC' AT TIME ZONE 'America/Guayaquil')::date
),

empleados_contrato AS (
    SELECT
        e.id  AS empleado_id,
        e.name AS empleado_nombre,
        rc.id AS calendario_id,
        c.date_start,
        CASE
            WHEN c.state = 'open' AND c.date_end IS NULL THEN (
                SELECT MAX((date_time AT TIME ZONE 'UTC' AT TIME ZONE 'America/Guayaquil')::date)
                FROM employee_attendance_raw
            )
            ELSE c.date_end
        END AS date_end
    FROM hr_employee e
    JOIN hr_contract c        ON c.employee_id = e.id
    JOIN resource_calendar rc ON rc.id = e.resource_calendar_id
    WHERE e.active = TRUE
      AND e.control_marcaciones
),

fechas AS (
    SELECT generate_series(l.fecha_min, l.fecha_max, interval '1 day')::date AS fecha
    FROM limites l
),

empleado_fechas AS (
    SELECT
        ec.empleado_id,
        ec.empleado_nombre,
        ec.calendario_id,
        f.fecha,
        -- Horarios teóricos como timestamps locales (pueden ser NULL en fines de semana)
        CASE WHEN MIN(rca.hour_from) IS NOT NULL THEN
            make_timestamp(
                EXTRACT(YEAR FROM f.fecha)::int,
                EXTRACT(MONTH FROM f.fecha)::int,
                EXTRACT(DAY FROM f.fecha)::int,
                floor(MIN(rca.hour_from))::int,
                ((MIN(rca.hour_from) - floor(MIN(rca.hour_from))) * 60)::int,
                0
            )
        END AS fecha_inicio,
        CASE WHEN MAX(rca.hour_to) IS NOT NULL THEN
            make_timestamp(
                EXTRACT(YEAR FROM f.fecha)::int,
                EXTRACT(MONTH FROM f.fecha)::int,
                EXTRACT(DAY FROM f.fecha)::int,
                floor(MAX(rca.hour_to))::int,
                ((MAX(rca.hour_to) - floor(MAX(rca.hour_to))) * 60)::int,
                0
            )
        END AS fecha_fin
    FROM empleados_contrato ec
    JOIN fechas f
      ON f.fecha BETWEEN ec.date_start AND ec.date_end
    JOIN resource_calendar rc
      ON rc.id = ec.calendario_id
    LEFT JOIN resource_calendar_attendance rca
      ON rca.calendar_id = rc.id
     AND rca.dayofweek::int = (EXTRACT(ISODOW FROM f.fecha)::int - 1) -- lunes=1..domingo=7  vs  0..6
    GROUP BY ec.empleado_id, ec.empleado_nombre, ec.calendario_id, f.fecha
),
feriados as (
	SELECT 
	    ch.id,
	    ch.name,
	    gs::date AS fecha
		FROM calendar_holiday ch
		JOIN calendar_legal_holiday clh 
		      ON ch.id = clh.holiday_id
		CROSS JOIN LATERAL generate_series(
		    clh.date_from::date,
		    clh.date_to::date,
		    interval '1 day'
		) gs
		ORDER BY ch.id, fecha
),
consolidado  as (

	SELECT
	    ROW_NUMBER() OVER() AS id,
	    e.id   AS empleado_id,
	    e.name AS empleado_nombre,
	    ef.fecha,
	    cd.id  AS day_id,
	
	    -- Entrada/salida reales (si no hay biometría, usa horario teórico; si tampoco hay, queda NULL)
	    COALESCE(m.entrada_real, m.salida_real, ef.fecha_inicio) AS entrada_real,
	    COALESCE(m.salida_real, m.entrada_real, ef.fecha_fin)    AS salida_real,
	
	    -- Horas como float_time (local)
	    EXTRACT(EPOCH FROM (COALESCE(m.entrada_real, m.salida_real, ef.fecha_inicio))::time) / 3600 AS entrada_hora,
	    EXTRACT(EPOCH FROM (COALESCE(m.salida_real,  m.entrada_real, ef.fecha_fin))::time)   / 3600 AS salida_hora,
	
	    rc.id AS calendario_id,
	    EXTRACT(ISODOW FROM ef.fecha)::int AS dia_semana,  -- 1=lun ... 7=dom
	
	    -- Horarios teóricos (float_time) protegidos para fines de semana (NULL si no hay horario)
	    CASE WHEN MIN(rca.hour_from) IS NOT NULL THEN
	        EXTRACT(EPOCH FROM make_time(
	            floor(MIN(rca.hour_from))::int,
	            ((MIN(rca.hour_from) - floor(MIN(rca.hour_from))) * 60)::int,
	            0
	        )) / 3600
	    END AS inicio,
	
	    CASE WHEN MAX(rca.hour_to) IS NOT NULL THEN
	        EXTRACT(EPOCH FROM make_time(
	            floor(MAX(rca.hour_to))::int,
	            ((MAX(rca.hour_to) - floor(MAX(rca.hour_to))) * 60)::int,
	            0
	        )) / 3600
	    END AS fin,
	
	    -- Estado marcación
	    CASE
	        WHEN m.entrada_real IS NULL OR m.salida_real IS NULL THEN 'incompleto'
	        ELSE 'completo'
	    END AS estado_marcacion,
	
	    -- DIFERENCIA MINUTOS ENTRADA
	    CASE
	        -- Fines de semana (sin horario): minutos totales marcados; si falta una marca, 0
	        WHEN MIN(rca.hour_from) IS NULL THEN
	            -COALESCE(ROUND(EXTRACT(EPOCH FROM (m.salida_real - m.entrada_real))/60), 0)
	        -- Día hábil y ausente: jornada teórica
	        WHEN m.entrada_real IS NULL AND m.salida_real IS NULL THEN
	            ROUND(EXTRACT(EPOCH FROM (ef.fecha_fin - ef.fecha_inicio))/60)
	        -- Día hábil con horario: programado - real
	        ELSE
	            -ROUND(EXTRACT(EPOCH FROM (
	                make_time(
	                    floor(MIN(rca.hour_from))::int,
	                    ((MIN(rca.hour_from) - floor(MIN(rca.hour_from))) * 60)::int,
	                    0
	                )
	                -
	                (COALESCE(m.entrada_real, m.salida_real, ef.fecha_inicio))::time
	            ))/60)
	    END AS dif_min_entrada,
	
	    -- Estado entrada (local)
	    CASE
	        WHEN MIN(rca.hour_from) IS NULL THEN 'sin_horario' -- sábado/domingo u otro día sin rca
	        WHEN m.entrada_real IS NULL AND m.salida_real IS NULL THEN 'ausente'
	        WHEN (COALESCE(m.entrada_real, m.salida_real))::time
	             < make_time(
	                 floor(MIN(rca.hour_from))::int,
	                 ((MIN(rca.hour_from) - floor(MIN(rca.hour_from))) * 60)::int,
	                 0
	               ) THEN 'temprano'
	        WHEN (COALESCE(m.entrada_real, m.salida_real))::time
	             = make_time(
	                 floor(MIN(rca.hour_from))::int,
	                 ((MIN(rca.hour_from) - floor(MIN(rca.hour_from))) * 60)::int,
	                 0
	               ) THEN 'puntual'
	        ELSE 'atraso'
	    END AS estado_entrada,
	
	    -- Diferencia minutos salida (real - programado). Si no hay horario, NULL.
	    CASE
	        WHEN MAX(rca.hour_to) IS NULL THEN NULL
	        ELSE
	            -ROUND(EXTRACT(EPOCH FROM (
	                (COALESCE(m.salida_real, m.entrada_real, ef.fecha_fin))::time
	                -
	                make_time(
	                    floor(MAX(rca.hour_to))::int,
	                    ((MAX(rca.hour_to) - floor(MAX(rca.hour_to))) * 60)::int,
	                    0
	                )
	            ))/60, 2)
	    END AS dif_min_salida,
	
	    -- Estado salida (local)
	    CASE
	        WHEN MAX(rca.hour_to) IS NULL THEN 'sin_horario'
	        WHEN m.salida_real IS NULL AND m.entrada_real IS NULL THEN 'ausente'
	        WHEN (COALESCE(m.salida_real, m.entrada_real))::time
	             < make_time(
	                 floor(MAX(rca.hour_to))::int,
	                 ((MAX(rca.hour_to) - floor(MAX(rca.hour_to))) * 60)::int,
	                 0
	               ) THEN 'anticipada'
	        WHEN (COALESCE(m.salida_real, m.entrada_real))::time
	             = make_time(
	                 floor(MAX(rca.hour_to))::int,
	                 ((MAX(rca.hour_to) - floor(MAX(rca.hour_to))) * 60)::int,
	                 0
	               ) THEN 'puntual'
	        ELSE 'tardia'
	    END AS estado_salida,
		f.id as feriado_id 
	
	FROM empleado_fechas ef
	JOIN hr_employee e
	  ON e.id = ef.empleado_id
	JOIN resource_calendar rc
	  ON rc.id = e.resource_calendar_id
	-- LEFT para NO perder sábados y domingos
	LEFT JOIN resource_calendar_attendance rca
	  ON rca.calendar_id = rc.id
	 AND rca.dayofweek::int = (EXTRACT(ISODOW FROM ef.fecha)::int - 1)
	-- LEFT para no filtrar domingos si faltan en calendar_day
	LEFT JOIN calendar_day cd
	  ON cd.value = (EXTRACT(ISODOW FROM ef.fecha)::int % 7)
	LEFT JOIN marcaciones m
	  ON m.employee_id = ef.empleado_id
	 AND m.fecha       = ef.fecha
	left join feriados f on f.fecha=ef.fecha   
	--WHERE
	  --e.name = 'MINO MERO ALFREDO ORLANDO'
	  --e.name = 'ZAMBRANO HERNANDEZ MATHEU JOSUE'
	--  e.name = 'CRESPIN MORAN LAJONNER ALFONSO'
	GROUP BY
	    e.id, e.name, ef.fecha,
	    m.entrada_real, m.salida_real,
	    rc.id, cd.id,
	    m.employee_id, ef.fecha_inicio, ef.fecha_fin,
		f.id 
	HAVING
	    NOT (
	      MIN(rca.hour_from) IS NULL
	      AND MAX(rca.hour_to) IS NULL
	      AND COALESCE(ROUND(EXTRACT(EPOCH FROM (m.salida_real - m.entrada_real))/60), 0) = 0
	  )
	ORDER BY e.id, ef.fecha

)

select *,
    -- Minutos a descontar
    CASE
        -- Ausente → se descuenta toda la jornada, si > 240 resto 30
        WHEN estado_entrada = 'ausente' AND estado_salida = 'ausente' AND feriado_id IS NULL THEN
            CASE 
                WHEN (ABS(dif_min_entrada) + ABS(dif_min_salida)) > 240
                THEN GREATEST((ABS(dif_min_entrada) + ABS(dif_min_salida)) - 30, 0)
                ELSE (ABS(dif_min_entrada) + ABS(dif_min_salida))
            END

        -- Atraso o salida anticipada
        WHEN estado_entrada = 'atraso' OR estado_salida = 'anticipada' THEN
            CASE
                WHEN (
                    (CASE WHEN estado_entrada = 'atraso' THEN ABS(dif_min_entrada) ELSE 0 END) +
                    (CASE WHEN estado_salida = 'anticipada' THEN ABS(dif_min_salida) ELSE 0 END)
                ) > 240
                THEN GREATEST(
                    (CASE WHEN estado_entrada = 'atraso' THEN ABS(dif_min_entrada) ELSE 0 END) +
                    (CASE WHEN estado_salida = 'anticipada' THEN ABS(dif_min_salida) ELSE 0 END) - 30,
                    0
                )
                ELSE
                    (CASE WHEN estado_entrada = 'atraso' THEN ABS(dif_min_entrada) ELSE 0 END) +
                    (CASE WHEN estado_salida = 'anticipada' THEN ABS(dif_min_salida) ELSE 0 END)
            END

        -- Sin horario → total real, si > 240 resto 30
        WHEN estado_entrada = 'sin_horario' AND estado_salida = 'sin_horario' THEN
            CASE 
                WHEN (ABS(dif_min_entrada) + ABS(dif_min_salida)) > 240
                THEN GREATEST((ABS(dif_min_entrada) + ABS(dif_min_salida)) - 30, 0)
                ELSE (ABS(dif_min_entrada) + ABS(dif_min_salida))
            END

        ELSE 0
    END AS minutos_descontar,

    -- Minutos extras
    CASE
        -- Ausente → no hay extras
        WHEN estado_entrada = 'ausente' AND estado_salida = 'ausente' THEN 0
        
        -- Sin horario → total, si > 240 resto 30
        WHEN estado_entrada = 'sin_horario' AND estado_salida = 'sin_horario' THEN
            CASE 
                WHEN (ABS(dif_min_entrada) + ABS(dif_min_salida)) > 240
                THEN (ABS(dif_min_entrada) + ABS(dif_min_salida)) - 30
                ELSE (ABS(dif_min_entrada) + ABS(dif_min_salida))
            END

        ELSE 0
    END AS minutos_extras
	
from consolidado 


        """)

	def _get_all_subordinates(self, employee):
		""" Devuelve todos los subordinados recursivos de un empleado """
		all_subordinates = self.env["hr.employee"]
		to_process = employee.child_ids
		while to_process:
			all_subordinates |= to_process
			to_process = to_process.mapped("child_ids")
		return all_subordinates

	@api.model
	def _where_calc(self, domain, active_test=True):
		domain = domain or []

		# Si no viene "only_user" en contexto, usar comportamiento normal
		if not self._context.get("only_user", False):
			return super(EmployeeAttendanceCalendar, self)._where_calc(domain, active_test)

		# Usuario actual
		user = self.env["res.users"].sudo().browse(self._uid)

		# Si es empleado "normal"
		if user.has_group("gps_hr.group_empleados_usuarios"):
			employee = self.env["hr.employee"].sudo().search([("user_id", "=", user.id)], limit=1)

			if employee:
				# ✅ incluir al empleado + todos los subordinados recursivos
				subordinates = self._get_all_subordinates(employee)
				employees_ids = employee.ids + subordinates.ids
				if not employees_ids:
					employees_ids = [-1]

				domain.append(("empleado_id", "in", employees_ids))
			else:
				domain.append(("empleado_id", "=", -1))

		return super(EmployeeAttendanceCalendar, self)._where_calc(domain, active_test)
