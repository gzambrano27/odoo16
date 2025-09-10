from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, timedelta
import calendar

class HrAbsence(models.Model):
    _name = "hr.absence"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Registro de Ausencias"

    name = fields.Char("Referencia", compute="_compute_name", store=True)
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True, tracking=True)
    company_id = fields.Many2one("res.company", string="Compañía", related="employee_id.company_id", store=True, readonly=True)
    contract_id = fields.Many2one(
        "hr.contract",
        string="Contrato",
        domain="[('employee_id','=',employee_id),('state','=','open')]",
        required=True,
        tracking=True
    )

    type_permisson = fields.Selection([
        ('partial', 'Parcial'),
        ('complete', 'Completo')
    ], string="Tipo de Permiso", default="partial", required=True, tracking=True)

    holiday_status_id = fields.Many2one(
        "hr.leave.type",
        string="Tipo de Ausencia",
        domain="['|', ('requires_allocation', '=', 'no'), '&', ('has_valid_allocation', '=', True), '&', ('virtual_remaining_leaves', '>', 0), ('max_leaves', '>', 0)]",
        context="{'employee_id': employee_id, 'default_date_from': request_date_from, 'default_date_to': request_date_to}",
        options="{'no_create': True, 'no_open': True, 'request_type':'leave'}",
        required=True,
        tracking=True
    )

    request_date_from = fields.Date("Fecha Desde", required=True, tracking=True)
    request_date_to = fields.Date("Fecha Hasta", tracking=True)
    request_hour_from = fields.Float("Hora Desde", widget="float_time")
    request_hour_to = fields.Float("Hora Hasta", widget="float_time")
    description = fields.Text("Descripción", tracking=True)

    state = fields.Selection([
	    ('draft', 'A Enviar'),
	    ('confirm', 'A Aprobar'),
	    ('validate', 'Aprobado'),
    ], string="Estado", default="draft", tracking=True)

    period_line_ids = fields.One2many("hr.absence.period.line", "request_id", string="Detalle Periodos")

    # -------- FUNCIONES ----------
    @api.model
    def get_vacation_period_ids(self, date_start, date_stop, contract_id, code, request_id=0):
        print((date_start, date_stop, contract_id, code, request_id))
        self._cr.execute(""";WITH VARIABLES AS (
                SELECT 
                %s::DATE AS DATE_START,
                %s::DATE AS DATE_END,
                %s::INT AS CONTRACT_ID,
                %s::INT AS REQUEST_ID 
                ),
                PERIOD_VACATIONS AS (
                SELECT 
                R.ID, 
                    ((R.ATTEMPT_DAYS-R.TAKEN_PENDING_MIGRATED_DAYS)-
                    COALESCE((SELECT SUM(L.DAYS) FROM HR_VACATION_PERIOD_LINE L WHERE L.REQUEST_ID!=VARIABLES.REQUEST_ID AND L.PERIOD_ID=R.ID),0)) AS PENDING_DAYS,
                R.YEAR_START,
                R.YEAR_END 
                FROM HR_VACATION_PERIOD R
                INNER JOIN VARIABLES ON 1=1
                WHERE R.CONTRACT_ID=VARIABLES.CONTRACT_ID AND R.STATE='confirmed' 
                ) ,
                GROUP_PERIOD_VACATIONS AS ( 
                    SELECT PERIOD_VACATIONS.* ,
                    COALESCE((SELECT SUM(X.PENDING_DAYS) 
                    FROM PERIOD_VACATIONS X WHERE X.YEAR_START<PERIOD_VACATIONS.YEAR_START),0) AS TOTAL_PENDING_START,
                    COALESCE((SELECT SUM(X.PENDING_DAYS) 
                    FROM PERIOD_VACATIONS X WHERE X.YEAR_END<=PERIOD_VACATIONS.YEAR_END),0) AS TOTAL_PENDING_END
                    FROM PERIOD_VACATIONS
                ),
                VACATION_DAYS AS (
                SELECT CAST(GENERATE_SERIES(DATE_START,DATE_END,'1 DAY'::INTERVAL) AS DATE) AS DATE 
                FROM VARIABLES
                ),
                ORDER_VACATION_DAYS AS (
                    SELECT ROW_NUMBER() OVER(ORDER BY DATE ASC) AS NUMBER,* FROM  VACATION_DAYS
                ) 

                SELECT G.ID,G.ID
                FROM ORDER_VACATION_DAYS O
                INNER JOIN VARIABLES ON 1=1
                LEFT JOIN GROUP_PERIOD_VACATIONS G ON O.NUMBER>G.TOTAL_PENDING_START AND O.NUMBER<=G.TOTAL_PENDING_END 
                WHERE G.ID IS NOT NULL  
                ORDER BY G.YEAR_START ASC""", (date_start, date_stop, contract_id, request_id))
        data = self._cr.fetchall()
        result = {}
        for key, value in data:
            result[key] = result.get(key, 0) + value
        return list(result.items())

    @api.onchange('contract_id','request_date_from','request_date_to','holiday_status_id','employee_id')
    def onchange_type(self):
        period_line_ids=[(5,)]
        if self.holiday_status_id and self.contract_id and self.request_date_from and self.request_date_to:
            if self.holiday_status_id.vacations:
                vacation_period_ids = self.get_vacation_period_ids(
                    self.request_date_from,
                    self.request_date_to,
                    self.contract_id.id if self.contract_id else -1,
                    self.holiday_status_id and (self.holiday_status_id.vacations and "VACATION" or ''),
                    request_id=(self._origin.id or 0)
                )
                print(vacation_period_ids)
                period_line_ids = self._onchange_request_dates(vacation_period_ids)
        self.period_line_ids = period_line_ids

    is_vacation = fields.Boolean("Es Vacación", compute="_compute_is_vacation", store=False)

    @api.depends("holiday_status_id")
    def _compute_is_vacation(self):
        for rec in self:
	        # si tienes el campo vacations en hr.leave.type
	        rec.is_vacation = bool(rec.holiday_status_id and getattr(rec.holiday_status_id, "vacations", False))

    def _float_to_time(self, value):
        """Convierte un float (ej. 8.5) a string HH:MM (ej. 08:30)"""
        if value is False:
	        return ""
        hours = int(value)
        minutes = int(round((value - hours) * 60))
        return f"{hours:02d}:{minutes:02d}"

    @api.depends("employee_id", "request_date_from", "request_date_to",
                 "request_hour_from", "request_hour_to", "type_permisson")
    def _compute_name(self):
	    for rec in self:
		    if rec.type_permisson == "complete":
			    if rec.request_date_from and rec.request_date_to:
				    rec.name = f"{rec.employee_id.name or ''} - {rec.request_date_from} al {rec.request_date_to}"
			    else:
				    rec.name = f"{rec.employee_id.name or ''} - Permiso Completo"
		    elif rec.type_permisson == "partial":
			    if rec.request_date_from and rec.request_hour_from and rec.request_hour_to:
				    hour_from = rec._float_to_time(rec.request_hour_from)
				    hour_to = rec._float_to_time(rec.request_hour_to)
				    rec.name = f"{rec.employee_id.name or ''} - {rec.request_date_from} ({hour_from}-{hour_to})"
			    else:
				    rec.name = f"{rec.employee_id.name or ''} - Permiso Parcial"
		    else:
			    rec.name = rec.employee_id.name or "Permiso"

    # 🔹 Funciones de cambio de estado
    def action_draft(self):
        for rec in self:
	        rec.state = 'draft'

    def action_confirm(self):
	    for rec in self:
		    if rec.type_permisson == 'partial':
			    if not rec.request_date_from or not rec.request_hour_from or not rec.request_hour_to:
				    raise ValidationError(_("Debe ingresar la fecha, hora desde y hora hasta para un permiso parcial."))
		    elif rec.type_permisson == 'complete':
			    if not rec.request_date_from or not rec.request_date_to:
				    raise ValidationError(_("Debe ingresar la fecha de inicio y fin para un permiso completo."))
		    else:
			    raise ValidationError(_("Tipo de permiso no válido."))

		    rec.state = 'confirm'

    def action_validate(self):
        for rec in self:
	        if rec.state != 'confirm':
		        raise ValidationError(_("Solo se puede aprobar desde estado 'A Probar'."))
	        rec.state = 'validate'


class HrAbsencePeriodLine(models.Model):
    _name = "hr.absence.period.line"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Detalle de Periodo de Ausencia"

    period_id = fields.Many2one("hr.vacation.period", "Periodo de Vacaciones", ondelete="cascade")
    request_id = fields.Many2one("hr.absence", "Solicitud de Ausencia", ondelete="cascade")
    days = fields.Integer("Día(s)", required=True, default=0, tracking=True)
    num_days = fields.Integer("Día(s) por Tomar de la Solicitud", required=True, default=0)
    max_day = fields.Integer("Día Límite dentro de la Solicitud", required=True, default=0)

    date_start = fields.Date(related="request_id.request_date_from", string="Fecha de Inicio", store=True, readonly=True, tracking=True)
    date_stop = fields.Date(related="request_id.request_date_to", string="Fecha de Fin", store=True, readonly=True, tracking=True)

    state = fields.Selection(
        selection=[
            ('draft', _('Por enviar')),
            ('confirm', _('Por aprobar')),
            ('refuse', _('Rechazado')),
            ('validate1', _('Segunda aprobación')),
            ('validate', _('Aprobado')),
            ('cancel', _('Cancelado')),
        ],
        string="Estado",
        store=True,
        readonly=True,
        tracking=True,
        compute="_compute_state",
    )

    payment_state = fields.Selection(
        selection=[
            ('draft', _('Por enviar')),
            ('confirm', _('Confirmado')),
            ('validate', _('Aprobado')),
            ('cancel', _('Cancelado')),
        ],
        string="Estado Pago",
        store=True,
        readonly=True,
        tracking=True,
        default="draft"
    )

    date = fields.Date("Fecha de Registro", required=True, default=fields.Date.context_today, tracking=True)
    liquidated = fields.Boolean("Liquidado", default=False, tracking=True)

    type = fields.Selection([
        ('request','Por Permiso'),
        ('migrated','Migración'),
        ('payment','Vacaciones Pagadas'),
    ], default="request", string="Tipo", required=True, tracking=True)

    detail_ids = fields.One2many("hr.absence.period.line.detail", "line_id", string="Detalle")
    description = fields.Text("Observación", tracking=True)

    vacation_pending_days = fields.Integer("Pendiente(s)", default=0, tracking=True)
    vacation_attempt_pending_days = fields.Integer("P. Tentativos(s)", default=0, tracking=True)
    vacation_attempt_days = fields.Integer("Días Tentativos", default=0, tracking=True)
    vacation_days = fields.Integer("Día(s)", default=0, tracking=True)

    name = fields.Char("Descripción", compute="_compute_name", store=True, readonly=True)

    _sql_constraints = [
        ("unique_period_request", "unique(period_id,request_id)", "Periodo de Vacaciones debe ser único por contrato")
    ]

    sequence = fields.Integer(string="Secuencia", compute="_compute_sequence", store=True)
    contract_id = fields.Many2one(related="request_id.contract_id", store=True, readonly=True)
    employee_id = fields.Many2one(related="request_id.employee_id", store=True, readonly=True)

    comments = fields.Text("Comentarios")
    company_id = fields.Many2one(related="request_id.company_id", store=True, readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=True, readonly=True)

    wage = fields.Monetary("Sueldo", default=0.00)
    total = fields.Monetary("Total a Pagar", default=0.00)

    # --------- CÓMPUTOS ---------
    @api.depends('request_id','type','request_id.state','payment_state')
    def _compute_state(self):
        for record in self:
            if record.type == 'request':
                record.state = record.request_id.state if record.request_id else None
            if record.type == 'migrated':
                record.state = 'validate'
            if record.type == 'payment':
                record.state = record.payment_state

    @api.depends('type')
    def _compute_sequence(self):
        for record in self:
            record.sequence = 1
            if record.type == 'migrated':
                record.sequence = 0

    _order = "sequence asc, date asc"

    @api.onchange('type','request_id','period_id','date')
    @api.depends('type','request_id','period_id','date')
    def _compute_name(self):
        for brw_each in self:
            if brw_each.type == 'request':
                brw_each.name = "PERMISO DEL %s AL %s" % (brw_each.request_id.request_date_from, brw_each.request_id.request_date_to)
            if brw_each.type == 'migrated':
                brw_each.name = "DIAS MIGRADOS DEL PERIODO %s AL %s" % (brw_each.period_id.year_start, brw_each.period_id.year_end)
            if brw_each.type == 'payment':
                brw_each.name = "DIAS PAGADOS DEL PERIODO %s AL %s" % (brw_each.period_id.year_start, brw_each.period_id.year_end)

    @api.onchange('period_id')
    def onchange_period_id(self):
        for brw_each in self:
            attempt_pending_days = 1
            vacation_pending_days = 0
            vacation_attempt_pending_days = 0
            vacation_attempt_days = 0
            vacation_days = 0
            description = None
            if brw_each.period_id:
                attempt_pending_days = min(brw_each.period_id.attempt_pending_days, brw_each.request_id and 1 or 0)
                vacation_pending_days = brw_each.period_id.pending_days
                vacation_attempt_pending_days = brw_each.period_id.attempt_pending_days
                vacation_attempt_days = brw_each.period_id.attempt_days
                vacation_days = brw_each.period_id.days
                description = "%s de %s temp.,%s de %s ganados" % (
                    vacation_attempt_pending_days, vacation_attempt_days,
                    vacation_pending_days, vacation_days
                )
            brw_each.days = attempt_pending_days
            brw_each.vacation_pending_days = vacation_pending_days
            brw_each.vacation_attempt_pending_days = vacation_attempt_pending_days
            brw_each.vacation_attempt_days = vacation_attempt_days
            brw_each.vacation_days = vacation_days
            brw_each.description = description

    @api.onchange('days','period_id')
    def _onchange_days(self):
        if self.period_id and self.days <= 0:
            raise ValidationError("El número de días debe ser mayor a 0.")

    # --------- MÉTODOS ---------
    def unlink(self):
        for brw_each in self:
            if brw_each.period_id.state == "ended":
                raise ValidationError(_("Periodo de Vacaciones %s finalizado") % (brw_each.period_id.name,))
            if brw_each.request_id and brw_each.request_id.state == "ended":
                raise ValidationError(_("Solicitud de Ausencia %s finalizada") % (brw_each.request_id.name,))
        return super(HrAbsencePeriodLine, self).unlink()

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record.generate_monthly_details()
        return record

    def write(self, vals):
        res = super().write(vals)
        self.generate_monthly_details()
        return res

    def generate_monthly_details(self):
        for line in self:
            line.detail_ids.unlink()
            date_from = line.date_start
            date_to = line.date_stop
            if not date_from or not date_to:
                continue
            current = date_from
            while current <= date_to:
                year = current.year
                month = current.month
                last_day_of_month = date(year, month, calendar.monthrange(year, month)[1])
                period_end = min(last_day_of_month, date_to)
                if not line.request_id or line.request_id.state != 'refuse':
                    self.env['hr.absence.period.line.detail'].create({
                        'line_id': line.id,
                        'period_id': line.period_id.id,
                        'request_id': line.request_id.id,
                        'date_start': current,
                        'date_stop': period_end,
                        'days': (period_end - current).days + 1
                    })
                current = period_end + timedelta(days=1)

    def action_confirm(self):
        for rec in self:
            if rec.payment_state != 'draft':
                raise ValidationError("Solo se puede confirmar líneas en estado 'Borrador'.")
            rec.write({"payment_state": "confirm"})
        return True

    def action_cancel(self):
        for rec in self:
            if rec.payment_state not in ['draft', 'confirm']:
                raise ValidationError("Solo se puede cancelar líneas en estado 'Borrador' o 'Confirmado'.")
            rec.write({"payment_state": "cancel"})
        return True

    def action_validate(self):
        for rec in self:
            if rec.payment_state not in ['confirm']:
                raise ValidationError("Solo se puede aprobar líneas en estado 'Confirmado'.")
            rec.write({"payment_state": "validate"})
        return True

class HrAbsencePeriodLineDetail(models.Model):
    _name = "hr.absence.period.line.detail"
    _description = "Subdetalle Mensual de Ausencia"

    period_id = fields.Many2one("hr.vacation.period", "Periodo de Vacaciones", ondelete="cascade")
    request_id = fields.Many2one("hr.absence", "Solicitud de Ausencia", ondelete="cascade")
    line_id = fields.Many2one("hr.absence.period.line", "Detalle", ondelete="cascade")
    days = fields.Integer("Días", default=0, required=True)
    date_start = fields.Date("Fecha Inicio")
    date_stop = fields.Date("Fecha Fin")

    year = fields.Integer("Año", compute="_compute_year_month", store=True)
    month = fields.Integer("Mes", compute="_compute_year_month", store=True)

    @api.depends("date_start")
    def _compute_year_month(self):
        for rec in self:
            if rec.date_start:
                rec.year = rec.date_start.year
                rec.month = rec.date_start.month
            else:
                rec.year, rec.month = 0, 0

class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    vacations = fields.Boolean("Es Vacación", default=False)
