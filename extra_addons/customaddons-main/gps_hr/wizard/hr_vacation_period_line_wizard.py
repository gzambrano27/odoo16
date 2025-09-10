from odoo import models, fields, api,_
from odoo.exceptions import ValidationError

class HrVacationPeriodLineWizard(models.TransientModel):
    _name = 'hr.vacation.period.line.wizard'
    _description = 'Wizard para agregar línea tipo Payment'

    @api.model
    def _get_default_period_line_ids(self):
        period_line_ids=[]
        # if self._context.get('default_type','')=='add':
        #     period_line_ids=self._context.get('active_ids',[])
        return [(6,0,period_line_ids)]

    @api.model
    def _get_default_company_id(self):
        print(self._context)
        if self._context.get('default_company_id', False):
            return self._context.get('default_company_id', False)
        if self._context.get('active_model', '') == 'hr.vacation.period.line':
            period_line_ids = self._context.get('active_ids', [])
            brw_line=self.env["hr.vacation.period.line"].sudo().browse(period_line_ids)
            return brw_line and brw_line[0].period_id.company_id.id or False
        if self._context.get('active_model', '') == 'hr.vacation.period':
            period_ids = self._context.get('active_ids', [])
            brw_period= self.env["hr.vacation.period"].sudo().browse(period_ids)
            return brw_period and brw_period[0].company_id.id or False
        return False

    type = fields.Selection([('add', 'Agregar'),
                                 ('payment', 'Pagar'),
                             ],default="add",string="Tipo",required=False)

    period_id = fields.Many2one('hr.vacation.period', string='Periodo de Vacaciones', required=False)
    days = fields.Integer('Días a Tomar', required=True, default=1)
    date = fields.Date('Fecha del Registro', required=True, default=fields.Date.context_today)

    company_id = fields.Many2one('res.company', string="Compañia",default=_get_default_company_id)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)

    wage = fields.Monetary('Sueldo', required=False, default=0.00,store=True,compute="_compute_total")
    total = fields.Monetary('Total a Pagar', required=False, default=0.00,store=True,compute="_compute_total")
    total_days = fields.Integer('Total Dias', required=False, default=0, store=True, compute="_compute_total")

    comments=fields.Text('Comentarios')

    period_line_ids=fields.Many2many('hr.vacation.period.line','vacations_period2pay_rel','wizard_id','period_line_id','Lineas a Pagar',default=_get_default_period_line_ids)

    only1by_employee=fields.Boolean("Un registro por Empleado",default=False)

    @api.depends('wage','days','type')
    @api.onchange('wage', 'days','type')
    def _compute_total(self):
        DEC=2
        for brw_each in self:
            if brw_each.type=='add':
                total_days = brw_each.period_id.attempt_pending_days#(ejemplo 15,16,17....)
                dias_a_cobrar =brw_each.days  # por ejemplo, porque el resto los va a gozar o no se le pagan
                sueldo_mensual = brw_each.period_id.contract_id.wage#salario

                total = (sueldo_mensual / 30.0) * dias_a_cobrar
                brw_each.total_days=total_days
                brw_each.wage=round(sueldo_mensual,DEC)
                brw_each.total = round(total,DEC)
            else:
                total=sum(brw_each.period_line_ids.mapped('total'))
                brw_each.total_days = 0
                brw_each.wage = 0
                brw_each.total = round(total, DEC)


    @api.constrains('days', 'period_id','type')
    def _check_days_not_greater_than_available(self):
        for brw in self:
            if brw.type=='add':
                dias_disponibles = brw.total_days or 0
                dias_a_cobrar = brw.days or 0
                if dias_a_cobrar > dias_disponibles:
                    raise ValidationError(
                        f"Los días a cobrar ({dias_a_cobrar}) no pueden ser mayores a los días disponibles ({dias_disponibles})."
                    )


    @api.onchange('type', 'period_id','period_line_ids')
    def onchange_type_period(self):
        DEC=2
        if self.type == 'add':
            if self.period_id:
                self.company_id = self.period_id.company_id
        else:
            self.company_id = self._context.get('company_id', False)
            total=sum(self.period_line_ids.mapped('total'))
            self.total=round(total,DEC)

    @api.constrains('days','type')
    def _check_days(self):
        for record in self:
            if record.type == 'add':
                if record.days <= 0:
                    raise ValidationError("Los días a tomar deben ser mayores a cero.")

    def action_add_payment_line(self):
        self.ensure_one()
        if self.type!='add':
            raise ValidationError(_("Esta opcion no es valida para este tipo"))
        if self.days<=0:
            raise ValidationError(_("Los dias definidos deben ser mayor a 0.00"))
        if self.total<=0:
            raise ValidationError(_("El total a pagar debe ser mayor a 0.00"))
        self.env['hr.vacation.period.line'].create({
            'period_id': self.period_id.id,
            'days': self.days,
            'num_days': self.days,
            'max_day': self.days,
            'type': 'payment',
            'date': self.date,
            'wage':self.wage,
            'total': self.total,
            'state':'draft',
            'comments':self.comments,
        })
        return self.env.ref("gps_hr.action_hr_vacation_period_line").read()[0]
        #return {'type': 'ir.actions.act_window_close'}

    def action_create_movement(self):
        brw_rule = self.env.ref('gps_hr.rule_VACACIONES_PAGADAS')
        def create_employee_mov(self):
            OBJ_MOVEMENT = self.env["hr.employee.movement"].sudo()

            brw_movement = OBJ_MOVEMENT.create({
                "company_id": self.period_line_ids[0].company_id.id,
                'filter_iess': True,
                'rule_id': brw_rule.id,
                "category_code": brw_rule.category_id.code,
                "category_id": brw_rule.category_id.id,
                "name": "/",
                "date_process": self.date,
                "type": "batch",
                "origin": "system"
            })
            brw_movement.onchange_rule_employee_id()
            brw_movement.update_date_info()
            return brw_movement
        self.ensure_one()
        company_ids = self.period_line_ids.mapped('period_id.company_id.id')
        if len(set(company_ids)) > 1:
            raise ValidationError("Todos los registros deben pertenecer a la misma compañía para pagar las vacaciones.")

        # Validación: estado confirmado
        not_confirmed = self.period_line_ids.filtered(lambda r: r.payment_state != 'confirm')
        if not_confirmed:
            raise ValidationError("Todos los registros deben estar en estado 'Confirmado' para continuar.")

        if self.type!='payment':
            raise ValidationError(_("Esta opcion no es valida para este tipo"))
        if self.total<=0:
            raise ValidationError(_("El total a pagar debe ser mayor a 0.00"))
        movement_ids=[]
        if not self.only1by_employee:
            brw_movement=create_employee_mov(self)
            line_ids = [(5,)]
            for brw_line in self.period_line_ids:
                line_ids.append((0,0,{
                    "company_id": brw_line.period_id.company_id.id,
                    "rule_id": brw_movement.rule_id.id,
                    "category_code": brw_rule.category_id.code,
                    "category_id": brw_rule.category_id.id,
                    "date_process": brw_movement.date_process,
                    "year": brw_movement.year,
                    "month_id": brw_movement.month_id.id,
                    "employee_id": brw_line.employee_id.id,
                    "contract_id": brw_line.contract_id.id,
                    "name": brw_movement.name,
                    "comments": _("CUOTA CALCULADA AUTOMATICAMENTE"),
                    "department_id": brw_line.contract_id.department_id.id,
                    "job_id": brw_line.contract_id.job_id.id,
                    "bank_account_id": brw_line.employee_id.bank_account_id and brw_line.employee_id.bank_account_id.id or False,
                    "origin": "compute",
                    "total": brw_line.total,
                    "total_historic":brw_line.total,
                    "quota": 1,
                    "type": brw_movement.type
                }))
                brw_line.write({"payment_state":"validate"})
            brw_movement.write({"line_ids":line_ids})
            brw_movement.action_approved()
            movement_ids.append(brw_movement.id)
        else:
            for brw_line in self.period_line_ids:
                brw_movement = create_employee_mov(self)
                line_ids = [
                    (5,),
                    (0, 0, {
                    "company_id": brw_movement.company_id.id,
                    "rule_id": brw_movement.rule_id.id,
                    "category_code": brw_movement.category_code,
                    "date_process": brw_movement.date_process,
                    "year": brw_movement.year,
                    "month_id": brw_movement.month_id.id,
                    "employee_id": brw_line.employee_id.id,
                    "contract_id": brw_line.contract_id.id,
                    "name": brw_movement.name,
                    "comments": _("CUOTA CALCULADA AUTOMATICAMENTE"),
                    "department_id": brw_line.contract_id.department_id.id,
                    "job_id": brw_line.contract_id.job_id.id,
                    "bank_account_id": brw_line.employee_id.bank_account_id and brw_line.employee_id.bank_account_id.id or False,
                    "origin": "compute",
                    "total": brw_line.total,
                    "total_historic":brw_line.total,
                    "quota": 1,
                    "type": brw_movement.type
                })
                ]
                brw_movement.write({"line_ids": line_ids})
                brw_movement.action_approved()
                brw_line.write({"payment_state": "validate"})
                movement_ids.append(brw_movement.id)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lotes de Ingresos',
            'res_model': 'hr.employee.movement',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', movement_ids), ('category_code', '=', 'IN'),  ('type', 'in', ('batch', 'batch_automatic'))],
            'context': {
                'default_type': 'batch',
                'default_category_code': 'IN',
            },
            'views': [
                (self.env.ref('gps_hr.hr_employee_movement_view_tree').id, 'tree'),
                (self.env.ref('gps_hr.hr_employee_movement_view_form').id, 'form')
            ],
            'search_view_id': self.env.ref('gps_hr.hr_employee_movement_view_search').id,
        }
