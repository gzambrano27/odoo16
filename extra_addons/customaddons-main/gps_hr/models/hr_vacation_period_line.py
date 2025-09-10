from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...calendar_days.tools import CalendarManager, DateManager, MonthManager

dtObj = DateManager()
from datetime import date, timedelta
import calendar

class HrVacationPeriodLine(models.Model):
    _name = "hr.vacation.period.line"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Detalle de Periodo de vacaciones"

    period_id = fields.Many2one("hr.vacation.period", "Periodo de Vacaciones", ondelete="cascade")
    request_id = fields.Many2one("hr.leave", "Solicitud", ondelete="cascade")
    days = fields.Integer("Dia(s)", required=True, default=0,tracking=True)
    num_days = fields.Integer("Dia(s) por Tomar de la Solicitud", required=True, default=0)
    max_day = fields.Integer("Dia Limite dentro de la Solicitud", required=True, default=0)

    date_start = fields.Date(related="request_id.request_date_from", string="Fecha de Inicio", store=True, readonly=True,tracking=True)
    date_stop = fields.Date(related="request_id.request_date_to", string="Fecha de Fin", store=True, readonly=True,tracking=True)
    state = fields.Selection(
        selection=[
            ('draft', _('Por enviar')),
            ('confirm', _('Por aprobar')),
            ('refuse', _('Rechazado')),
            ('validate1', _('Segunda aprobación')),
            ('validate', _('Aprobado')),
            ('cancel', _('Cancelado')),
        ],
        string='Estado',
        store=True,
        readonly=True,tracking=True,
        compute='_compute_state',
    )

    payment_state = fields.Selection(
        selection=[
            ('draft', _('Por enviar')),
            ('confirm', _('Confirmado')),
            ('validate', _('Aprobado')),
            ('cancel', _('Cancelado')),
        ],
        string='Estado',
        store=True,
        readonly=True, tracking=True,default="draft"
    )



    date=fields.Date("Fecha de Registro",required=True,default=fields.Date.context_today,tracking=True)

    liquidated=fields.Boolean("Liquidado",default=False,tracking=True)
    type=fields.Selection([
        ('request','Por Permiso'),
        ('migrated','Migracion'),
        ('payment','Vacaciones Pagadas')

    ],default="request",string="Tipo",required=True,tracking=True)

    detail_ids=fields.One2many("hr.vacation.period.line.detail","line_id", "Detalle")

    description = fields.Text('Observacion',tracking=True)

    vacation_pending_days = fields.Integer("Pendiente(s)", default=0,tracking=True)
    vacation_attempt_pending_days = fields.Integer("P. Tentativos(s)", default=0,tracking=True)
    vacation_attempt_days = fields.Integer("Dias Tentativos", default=0,tracking=True)
    vacation_days = fields.Integer("Dia(s)", default=0,tracking=True)

    name=fields.Char("Descripcion",compute="_compute_name",store=True,readonly=True)

    _sql_constraints = [
        ("unique_period_request", "unique(period_id,request_id)", "Periodo de Vacaciones debe ser único por contrato")
    ]

    sequence = fields.Integer(string="Secuencia", compute="_compute_sequence", store=True)

    contract_id=fields.Many2one(related="period_id.contract_id",store=True,readonly=True)
    employee_id = fields.Many2one(related="period_id.employee_id", store=True, readonly=True)

    comments=fields.Text("Comentarios")

    company_id = fields.Many2one(related="period_id.company_id", store=True, readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=True, readonly=True)

    wage=fields.Monetary('Sueldo',default=0.00)
    total = fields.Monetary('Total a Pagar',default=0.00)



    @api.depends('request_id','type','request_id.state','payment_state')
    def _compute_state(self):
        for record in self:
            if record.type=='request':
                record.state = record.request_id.state if record.request_id else None
            if record.type=='migrated':
                record.state='validate'
            if record.type=='payment':
                record.state=record.payment_state

    @api.depends('type')
    def _compute_sequence(self):
        for record in self:
            record.sequence = 1
            if record.type == 'migrated':
                record.sequence = 0


    _order="sequence asc,date asc"

    @api.onchange('type','request_id','period_id','date')
    @api.depends('type','request_id','period_id','date')
    def _compute_name(self):
        for brw_each in self:
            if brw_each.type=='request':
                brw_each.name="PERMISO DEL %s AL %s" % (brw_each.request_id.request_date_from,brw_each.request_id.request_date_to)
            if brw_each.type == 'migrated':
                brw_each.name = "DIAS MIGRADOS DEL PERIODO %s AL %s" % (brw_each.period_id.year_start,brw_each.period_id.year_end)
            if brw_each.type == 'payment':
                brw_each.name = "DIAS PAGADOS DEL PERIODO %s AL %s" % (brw_each.period_id.year_start,brw_each.period_id.year_end)

    @api.onchange('period_id')
    def onchange_period_id(self):
        for brw_each in self:
            attempt_pending_days=1
            vacation_pending_days=0
            vacation_attempt_pending_days=0
            vacation_attempt_days = 0
            vacation_days = 0
            description=None
            if brw_each.period_id:
                attempt_pending_days = min(brw_each.period_id.attempt_pending_days,brw_each.request_id.number_of_days)
                vacation_pending_days=brw_each.period_id.pending_days
                vacation_attempt_pending_days = brw_each.period_id.attempt_pending_days
                vacation_attempt_days = brw_each.period_id.attempt_days
                vacation_days = brw_each.period_id.days
                description="%s de %s temp.,%s de %s ganados" % (vacation_attempt_pending_days,vacation_attempt_days,vacation_pending_days,vacation_days)
            brw_each.days=attempt_pending_days
            brw_each.vacation_pending_days=vacation_pending_days
            brw_each.vacation_attempt_pending_days = vacation_attempt_pending_days
            brw_each.vacation_attempt_days = vacation_attempt_days
            brw_each.vacation_days = vacation_days
            brw_each.description = description

    @api.onchange('days', 'period_id')
    def _onchange_days(self):
        if self.period_id:
            if self.days <= 0:
                raise ValidationError("El número de días debe ser mayor a 0.")
            # if self.period_id and self.days > self.period_id.attempt_pending_days:
            #     raise ValidationError(
            #         "El número de días no puede ser mayor que los días pendientes en el período de vacaciones.")


    def unlink(self):
        for brw_each in self:
            if brw_each.period_id.state == "ended":
                raise ValidationError(_("Periodo de Vacaciones %s finalizado") % (brw_each.period_id.name,))
            if brw_each.request_id.state == "ended":
                raise ValidationError(_("Solicitud de Vacaciones %s finalizada") % (brw_each.request_id.full_name,))
        return super(HrVacationPeriodLine, self).unlink()

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

                # Día final del mes actual o la fecha de fin, lo que ocurra primero
                last_day_of_month = date(year, month, calendar.monthrange(year, month)[1])
                period_end = min(last_day_of_month, date_to)
                if line.request_id.state!='refuse':
                    # Crear línea de detalle
                    self.env['hr.vacation.period.line.detail'].create({
                        'line_id': line.id,
                        'period_id': line.period_id.id,
                        'request_id': line.request_id.id,
                        'date_start': current,
                        'date_stop': period_end,
                        'days': (period_end - current).days + 1
                    })

                    # Avanzar al siguiente mes
                current = period_end + timedelta(days=1)

    def action_confirm(self):
        for brw_each in self:
            if brw_each.payment_state != 'draft':
                raise ValidationError("Solo se puede confirmar líneas en estado 'Borrador'.")
            brw_each.write({"payment_state": "confirm"})
        return True

    def action_cancel(self):
        for brw_each in self:
            if brw_each.payment_state not in ['draft', 'confirm']:
                raise ValidationError("Solo se puede cancelar líneas en estado 'Borrador' o 'Confirmado'.")
            brw_each.write({"payment_state": "cancel"})
        return True

    def action_validate(self):
        for brw_each in self:
            if brw_each.payment_state not in ['confirm']:
                raise ValidationError("Solo se puede aprobar lineas en estado 'Confirmado'")
            brw_each.write({"payment_state": "validate"})
        return True

    def action_pagar_vacaciones(self):
        self.ensure_one()  # opcional si solo debe ser usado sobre un registro
        records = self
        view_id = self.env.ref('gps_hr.view_hr_vacation_period_line_payment_wizard_form').id
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Pagar Vacaciones',
            'res_model': 'hr.vacation.period.line.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id':view_id,
            'context': {
                'default_type': 'payment',
                'lock_for1_payment': False,
                'default_period_line_ids': records.ids,
                'active_ids': records.ids,
                'active_id': records.id
            }
        }
        return action


