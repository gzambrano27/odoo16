# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from fontTools.misc.psCharStrings import read_byte
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.tools.config import config
from ...message_dialog.tools import FileManager
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager

fileO = FileManager()
dateO = DateManager()
calendarO = CalendarManager()
from datetime import datetime, timedelta


class HrEmployeeLiquidation(models.Model):
    _inherit = "hr.employee.document"
    _name = "hr.employee.liquidation"
    _description = "Liquidacion de Empleados"

    state = fields.Selection([('draft', 'Preliminar'),
                              ('verified', 'Por Verificar'),
                              ('approved', 'Aprobado'),
                              ('sended', 'Enviado'),
                              ('cancelled', 'Anulado'),
                              ('paid', 'Pagado'),
                              ('liquidated', 'Liquidado')], default="draft", required=True, string="Estado",tracking=True)

    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company, tracking=True
    )

    total = fields.Monetary(store=True, compute="_compute_total",tracking=True)

    total_to_paid = fields.Monetary(store=True, compute="_compute_total",tracking=True)
    total_paid = fields.Monetary(store=True, compute="_compute_total",tracking=True)
    total_pending = fields.Monetary(store=True, compute="_compute_total",tracking=True)

    type=fields.Selection([('liquidation','Liquidacion'),
                           ('vacation','Vacacion')],string="Tipo de Documento",required=True,default="liquidation",tracking=True)

    type_vacation = fields.Selection([('pagado', 'Pagadas'),
                             ('gozado', 'Gozadas')], string="Tipo", required=True, default="gozado",tracking=True)

    vacation_period_id=fields.Many2one('hr.vacation.period','Periodo',tracking=True)

    historic_line_ids=fields.Many2many('hr.employee.historic.lines','hr_employee_lines_historic_rel','liquidation_id','line_id','Detalle')

    vacation_date_start=fields.Date(related='vacation_period_id.date_start',store=False,readonly=True)
    vacation_date_end = fields.Date(related='vacation_period_id.date_end', store=False, readonly=True)

    _check_company_auto = True

    attempt_days = fields.Integer("Dias Tentativos", required=True, default=0,tracking=True)
    days = fields.Integer("Dia(s)", required=True, default=0,tracking=True)

    rule_id=fields.Many2one('hr.salary.rule',string="Rubro",required=False)

    pending_days = fields.Integer("Pendiente(s)", default=0 ,tracking=True)
    attempt_pending_days = fields.Integer("P. Tentativos(s)", default=0 ,tracking=True)
    total_taken_days = fields.Integer(  string="Total Dias Utilizados", default=0,tracking=True)

    category_code = fields.Char(string="Código de Categoría", required=False)
    category_id = fields.Many2one("hr.salary.rule.category", string="Categoría",required=False)


    request_ids = fields.Many2many('hr.leave', 'liquidation_leave_vac_rel', 'liquidation_id', 'leave_id',
                                  'Permisos')

    liquidation_line_ids=fields.One2many('hr.employee.liquidation.line','liquidation_id','Detalle',domain=[('type','=','liquidation')])
    last_payslip_ids = fields.One2many('hr.employee.liquidation.line', 'liquidation_id', 'Rol',domain=[('type','=','payslip')])

    input_line_ids = fields.One2many('hr.payslip.input', 'liquidation_id', 'Rubros',domain="[('movement_id','!=',False)]")
    new_input_line_ids= fields.One2many('hr.payslip.input', 'new_liquidation_id', 'Nuevos Rubros',domain="[('movement_id','=',False)]")

    account_ids=fields.One2many("hr.employee.liquidation.account","liquidation_id","Cuentas",tracking=True)

    move_id=fields.Many2one('account.move','Asiento Contable',tracking=True)

    date_for_payment=fields.Date("Fecha a Pagar",default=None,tracking=True)
    date_for_account = fields.Date("Fecha para Contabilizar", default=None, tracking=True)


    date_liquidation = fields.Date("Fecha de Acta de Finiquito", default=None, tracking=True)

    date_start=fields.Date("Fecha de Inicio",tracking=True)
    date_end= fields.Date("Fecha de Finalizacion",tracking=True)

    type_liquidation=fields.Selection([('renuncia_voluntaria','Renuncia Voluntaria'),
                                       ('despido_intepestivo', 'Despido Intepestivo'),
                                       ('terminacion_contrato', 'Terminacion de Obra/Contrato'),
                                       ],string="Tipo de Finiquito",default="renuncia_voluntaria",tracking=True)

    payslip_ids = fields.Many2many(
        'hr.payslip',
        string='Nóminas del contrato',
        compute='_compute_payslip_ids',
        store=False,
    )
    rule_ids=fields.Many2many(
        'hr.salary.rule',
        string='Reglas de Salario',
        compute='_compute_payslip_ids',
        store=False
    )
    dias_contrato = fields.Integer(string='Días del Contrato',tracking=True, compute='_compute_duracion_contrato', store=True)
    anios_contrato = fields.Integer(string='Años Completos del Contrato', compute='_compute_duracion_contrato',
                                    store=True,tracking=True)

    employee_ids = fields.Many2many(
        'hr.employee',
        string='Empleados',
        compute='_compute_employee_ids',
        store=False,context={'active_test':False}
    )

    payment_id = fields.Many2one('account.payment', 'Pago',tracking=True)

    do_account=fields.Boolean("Contabilizar",default=True,tracking=True)
    period_ids=fields.Many2many('hr.vacation.period','liquidation_periods_vac_rel','liquidation_id','period_id','Periodos de Vacaciones')

    last_payslip_id=fields.Many2one('hr.payslip','Ultimo Rol Completo')

    provision_ids = fields.Many2many('hr.employee.historic.lines', 'liq_doc_provision_rel','liquidation_id','provision_id','Provision')

    nopaid_days = fields.Integer("Dias no pagados", default=0, tracking=True)
    wage = fields.Monetary("Salario", default=0.00, tracking=True)
    legal_basic_wages= fields.Monetary("Salario Basico",compute="_compute_basic_infos" ,default=0.00, tracking=True,store=True)

    total_in = fields.Monetary("Ingresos", digits=(16, 2), required=False, default=0.00, store=True,
                               compute="update_payslip_total")
    total_out = fields.Monetary("Egresos", digits=(16, 2), required=False, default=0.00, store=True,
                                compute="update_payslip_total")
    total_provision = fields.Monetary("Provisión", digits=(16, 2), required=False, default=0.00, store=True,
                                      compute="update_payslip_total")
    total_payslip = fields.Monetary("Total", digits=(16, 2), required=False, default=0.00, store=True,
                                    compute="update_payslip_total")

    currency_id=fields.Many2one(related='company_id.currency_id',store=False,readonly=True,string="Moneda")

    pay_with_transfer = fields.Boolean("Pagar con Transferencia", default=True)

    month_id = fields.Many2one("calendar.month", "Mes",compute="_compute_date_infos",store=True)
    year = fields.Integer("Año", required=True,compute="_compute_date_infos",store=True)

    total_in_liquidation = fields.Monetary("Ingresos", digits=(16, 2), required=False, default=0.00, store=True,
                               compute="_compute_liquidation_total")
    total_out_liquidation = fields.Monetary("Egresos", digits=(16, 2), required=False, default=0.00, store=True,
                                compute="_compute_liquidation_total")
    total_provision_liquidation = fields.Monetary("Provisión", digits=(16, 2), required=False, default=0.00, store=True,
                                      compute="_compute_liquidation_total")
    total_liquidation = fields.Monetary("Total", digits=(16, 2), required=False, default=0.00, store=True,
                                    compute="_compute_liquidation_total")


    @api.onchange('date_for_account')
    @api.depends('date_for_account')
    def _compute_date_infos(self):
        for brw_each in self:
            brw_month=self.env["calendar.month"]
            if brw_each.date_for_account:
                brw_month=self.env["calendar.month"].sudo().search([('value','=',brw_each.date_for_account.month)])
            brw_each.year = brw_each.date_for_account and brw_each.date_for_account.year or False
            brw_each.month_id = brw_month and brw_month.id or False

    @api.onchange('date_process')
    @api.depends('date_process')
    def _compute_basic_infos(self):
        for brw_each in self:
            srch_legal = self.env["th.legal.wages"].sudo().search([('name', '=', brw_each.date_process.year)])
            legal_basic_wages = 0.00
            if srch_legal:
                legal_basic_wages = srch_legal[0].basic_wages
            brw_each.legal_basic_wages = legal_basic_wages

    @api.depends('company_id', 'type')
    def _compute_employee_ids(self):
        for brw_each in self:
            state = 'close' if brw_each.type == 'liquidation' else 'open'

            query = """
                    SELECT DISTINCT c.employee_id
                    FROM hr_contract c
                    JOIN hr_contract_type ct ON ct.id = c.contract_type_id
                    WHERE c.state = %s
                      AND c.company_id = %s
                      AND ct.legal_iess = TRUE
                      AND c.employee_id IS NOT NULL
                """
            self.env.cr.execute(query, (state, brw_each.company_id.id))
            rows = self.env.cr.fetchall()
            employee_ids = [row[0] for row in rows if row[0]]

            brw_each.employee_ids = [(6, 0, employee_ids)]

    @api.depends('contract_id', 'employee_id')
    def _compute_payslip_ids(self):
        def get_last_payslip_id(payslip_ids):
            #last_payslip= payslip_ids and payslip_ids[0]
            for each_payslip in payslip_ids:
                #sum_days=sum(each_payslip.worked_days_line_ids.mapped('number_of_days'))
                #if sum_days>=30:
                return each_payslip
            return False
        def calcular_dias(last_date_to,date_end,last_payslip_id):
            #sumar:last_date_to +1 hasta
            #date_end pero los dias calculados no pueden superar los 30 y en caso de febrero se debe ajustar a 30
            date_from=last_date_to
            if last_payslip_id:
                date_from=last_date_to+ timedelta(days=1)
            worked_days,top_days = self.env["dynamic.function"].sudo().function("compute_last_days", {},
                                                                       *[date_from, date_end,last_payslip_id,30])
            return worked_days,top_days

        for rec in self:
            if rec.contract_id and rec.employee_id:
                payslip_ids = self.env['hr.payslip'].search([
                    ('contract_id', '=', rec.contract_id.id),
                    ('employee_id', '=', rec.employee_id.id),
                ],order="date_from desc")
                rec.payslip_ids=payslip_ids
                rec.rule_ids = [(6,0,rec.mapped('liquidation_line_ids.rule_id').ids)]
                period_ids=self.env["hr.vacation.period"].sudo().search([
                    ('contract_id', '=', rec.contract_id.id),
                    ('employee_id', '=', rec.employee_id.id),
                ])
                rec.period_ids=[(6, 0, period_ids and period_ids.ids or [])]

                request_ids = self.env["hr.leave"].sudo().search([
                    ('contract_id', '=', rec.contract_id.id),
                    ('employee_id', '=', rec.employee_id.id),
                ])
                rec.request_ids = [(6, 0, request_ids and request_ids.ids or [])]
                rec.last_payslip_id = get_last_payslip_id(payslip_ids)

                provision_ids= self.env["hr.employee.historic.lines"].sudo().search([
                    ('company_id', '=', rec.company_id.id),
                    ('state', '=','posted'),
                    ('employee_id', '=', rec.employee_id.id),
                    ('rule_id.code', 'in', ('PROV_TERCERO','PROV_CUARTO','PROV_VAC') ),
                    ('rule_id.legal_iess', '=',True),

                    ('date_to', '>=', rec.date_start),
                    ('date_from', '<=', rec.date_end),
                ])
                nopaid_days= calcular_dias(rec.date_start,rec.date_end,rec.last_payslip_id) [0]
                rec.provision_ids=[(6,0,provision_ids and provision_ids.ids or [])]
                rec.nopaid_days=nopaid_days
                rec.wage=rec.contract_id.wage
            else:
                rec.payslip_ids = [(6, 0, [])]  # Vaciar
                rec.request_ids=[(6,0,[])]
                rec.period_ids = [(6, 0, [])]
                rec.rule_ids=[(6,0,rec.mapped('liquidation_line_ids.rule_id').ids)]
                rec.last_payslip_id=False
                rec.provision_ids=[(6,0,[])]
                rec.nopaid_days=0
                rec.wage=0.00

    @api.depends('contract_id','contract_id.date_start', 'contract_id.date_end')
    @api.onchange('contract_id','contract_id.date_start', 'contract_id.date_end')
    def _compute_duracion_contrato(self):
        for rec in self:
            fecha_inicio = rec.contract_id.date_start
            fecha_fin = rec.contract_id.date_end or fields.Date.context_today(rec)
            if fecha_inicio and fecha_fin and fecha_fin >= fecha_inicio:
                delta = fecha_fin - fecha_inicio
                dias_contrato = delta.days + 1
                anios_contrato=0
                # Ajustar cálculo de años para que cuente como 1 si tiene >= 365 días
                if dias_contrato >= 365:
                    anios_contrato = dias_contrato // 365
                #print(anios_contrato,dias_contrato // 365)
                rec.anios_contrato = anios_contrato
                rec.dias_contrato = dias_contrato
                rec.date_liquidation = fecha_fin
            else:
                rec.dias_contrato = 0
                rec.anios_contrato = 0
                rec.date_liquidation = None

    def unlink(self):
        move_lines = self.env["hr.employee.movement.line"]
        # Verificar si algún registro no está en estado 'draft'
        if any(brw_each.state != 'draft' for brw_each in self):
            raise ValidationError(_("No puedes borrar un registro que no sea preliminar"))
        # Mapeo de líneas de entrada en una sola operación
        inputs = self.mapped('input_line_ids.movement_id')
        move_lines += inputs
        # Llamar al metodo unlink del superclase
        values = super(HrEmployeeLiquidation, self).unlink()
        # Calcular total solo si hay líneas de movimiento
        if move_lines:
            move_lines._compute_total()
        return values

    @api.model
    def get_new_inputs(self, contracts):
        # TODO: We leave date_from and date_to params here for backwards
        # compatibility reasons for the ones who inherit this function
        # in another modules, but they are not used.
        # Will be removed in next versions.
        """
        Inputs computation.
        @returns: Returns a dict with the inputs that are fetched from the salary_structure
        associated rules for the given contracts.
        """
        OBJ_LINE = self.env["hr.employee.movement.line"].sudo()
        res = [(5,)]
        for contract in contracts:
            current_structure = contract.contract_type_id.struct_id
            rule_ids = current_structure.struct_rule_ids and current_structure.struct_rule_ids.ids or []
            rule_ids += [-1, -1]
            line_srch = OBJ_LINE.search(
                [
                 ('company_id', '=', contract.company_id.id),
                 ('contract_id', '=', contract.id),
                 ('employee_id', '=', contract.employee_id.id),
                 ('total_pending', '>', 0),
                 ('state', '=', 'approved'),
                 ('rule_id', 'in', rule_ids)
                 ])
            if line_srch:
                for brw_line in line_srch:
                    self.register_movement(contract.id, res, brw_line)
        return res

    @api.model
    def register_movement(self, contract_id, lst, brw_line):
        lst.append((0, 0, {"contract_id": contract_id,
                           "code": brw_line.rule_id.code,
                           "sequence": len(lst) + 1,
                           "name": brw_line.name,
                           "amount": brw_line.total_pending,  # monto por aplicar
                           "original_pending": brw_line.total_pending,  # monto por pendiente
                           "original_amount": brw_line.total_to_paid,  # monto original
                           "rule_id": brw_line.rule_id.id,
                           "category_id": brw_line.rule_id.category_id.id,
                           "movement_id": brw_line.id,
                           "add_iess": (brw_line.rule_id.category_code == 'IN' and brw_line.rule_id.add_iess or False),
                           "date_process": brw_line.date_process,
                           "quota": brw_line.quota,
                           "force_payslip": brw_line.rule_id.force_payslip,
                           "movement_ref_id": "%s/%s" % (brw_line.process_id.id, brw_line.id),
                           }))  #
        return lst


    @api.onchange('company_id')
    def onchange_company_id(self):
        self.contract_id=False

    @api.onchange('type','employee_id','company_id')
    def onchange_employee_id(self):
        domain=('open','close')
        if self.type=='liquidation':
            domain = ('close',)
        srch_contract = self.env["hr.contract"].sudo().search([('company_id','=',self.company_id.id),
                                                               ('employee_id', '=', self.employee_id.id),
                                                               ('state','in',domain),
                                                               ('contract_type_id.legal_iess','=',True)
                                                               ],order="date_start desc",limit=1)
        if srch_contract:
            self.contract_id = srch_contract.id
            if self.contract_id:
                name="LIQUIDACION DE VACACIONES PARA %s " % (self.contract_id.name,)
                if self.type == 'liquidation':
                    name="LIQUIDACION DE HABERES PARA %s " % (self.contract_id.name,)
                self.name=name
                self.date_start=self.contract_id.date_start
                self.date_end = self.contract_id.date_end
                self.date_for_account=self.contract_id.date_end
        else:
            self.contract_id = False
            self.name=None
            self.date_start=None
            self.date_end = None
            self.date_for_account =None

    @api.onchange('type_vacation','type')
    def onchange_type_vacation(self):
        if self.type=='vacation':
            if self.type_vacation=='gozado':
                self.rule_id=self.env.ref('gps_hr.rule_PROV_VACACIONES').id
                self.category_code = self.rule_id.category_id.code
                self.category_id = self.rule_id.category_id.id
            else:
                self.rule_id = self.env.ref('gps_hr.rule_VACACIONES_PAGADAS').id
                self.category_code = self.rule_id.category_id.code
                self.category_id = self.rule_id.category_id.id
        else:
            self.rule_id=False
            self.category_code=None
            self.category_id=False


    @api.onchange('rule_id', 'employee_id','vacation_period_id')
    def onchange_type_vacation_rules(self):
        if self.employee_id:
            if self.type == 'vacation':
                if self.type_vacation == 'gozado':
                    self.name="VACACIONES GOZADAS DE %s PERIODO %s" % (self.employee_id.name,self.vacation_period_id.name)
                else:
                    self.name="VACACIONES PAGADAS DE %s PERIODO %s" % (self.employee_id.name,self.vacation_period_id.name)
        else:
            self.name=None

    def _get_localdict(self):
        self.ensure_one()
        localdict = {}
        new_fx = self.env["dynamic.function"].sudo().initialize()
        localdict.update(new_fx[0])
        return localdict

    def restore_movements(self):
        for brw_each in self:
            # liquidation_line_ids = [(5,)]
            # rule_ids = brw_each.contract_id.contract_type_id.struct_id.struct_rule_ids
            # if rule_ids:
            #     sequence = 1
            #     rule_ids = rule_ids.filtered(lambda x: x.category_id != self.env.ref('gps_hr.type_provision'))
            #     for brw_rule in rule_ids:
            #         rule_type = 'income' if brw_rule.category_id == self.env.ref('gps_hr.type_income') else 'expense'
            #         if rule_type == 'income':
            #             if not brw_rule.legal_iess:
            #                 continue
            #         liquidation_line_ids.append((0, 0, {
            #                 "rule_id": brw_rule.id,
            #                 "name": brw_rule.name,
            #                 "transaction_type": rule_type,
            #                 "amount": 0.00,
            #                 "amount_original": 0.00,
            #                 "sequence": sequence,
            #                 'type':'liquidation',
            #                 "category_id":brw_rule.category_id.id
            #         }))
            #         sequence += 1
            input_line_ids = brw_each.get_new_inputs(brw_each.contract_id)
            #brw_each.liquidation_line_ids = liquidation_line_ids
            brw_each.input_line_ids = input_line_ids
            brw_each.compute_rules()

    @api.onchange('contract_id')
    def onchange_contract_id(self):
        if self.contract_id:
            self.date_start = self.contract_id.date_start
            self.date_end = self.contract_id.date_end
            self.job_id = self.contract_id.job_id.id
            self.department_id = self.contract_id.department_id.id
            self.restore_movements()
        else:
            self.date_start = None
            self.date_end = None
            self.job_id = False
            self.department_id = False
            self.liquidation_line_ids=[(5,)]
            self.input_line_ids=[(5,)]

    @api.onchange('company_id','contract_id','vacation_period_id','type_vacation')
    def onchange_period_id(self):
        if not self.vacation_period_id:
            self.historic_line_ids=[(6,0,[])]
            self.vacation_date_start=None
            self.vacation_date_end = None
            self.attempt_days=0
            self.days=0
            self.pending_days = 0
            self.attempt_pending_days = 0
            self.total_taken_days=0
        else:
            date_start= self.vacation_period_id.date_start
            date_end = self.vacation_period_id.date_end
            rubro_id=self.env.ref('gps_hr.rule_PROV_VACACIONES').id
            self._cr.execute(""";WITH VARIABLES AS (
	SELECT %s::INT AS COMPANY_ID,
		 %s::INT AS EMPLOYEE_ID,
		 %s::INT AS RULE_ID,
		 %s::DATE AS DATE_FROM,
		 %s::DATE AS DATE_TO 
) 

SELECT HHL.ID,HHL.ID FROM 
VARIABLES 
INNER JOIN HR_EMPLOYEE_HISTORIC_LINES HHL ON  HHL.COMPANY_ID=VARIABLES.COMPANY_ID AND 
		HHL.EMPLOYEE_ID=VARIABLES.EMPLOYEE_ID AND 
		HHL.RULE_ID=VARIABLES.RULE_ID 
WHERE 	(HHL.DATE_FROM>=HHL.DATE_FROM AND HHL.DATE_TO<=HHL.DATE_TO)     """,(self.company_id.id,self.employee_id.id,
                                      rubro_id,
                                      self.vacation_date_start,self.vacation_date_end
                                      ))
            result=self._cr.fetchall()
            line_ids=[*dict(result)]
            self.historic_line_ids=[(6,0,line_ids and line_ids or [])]
            self.vacation_date_start = date_start
            self.vacation_date_end =date_end
            self.attempt_days = self.vacation_period_id.attempt_days
            self.days = self.vacation_period_id.days
            self.pending_days = self.vacation_period_id.pending_days
            self.attempt_pending_days = self.vacation_period_id.attempt_pending_days
            self.total_taken_days=self.vacation_period_id.total_taken_days

    # @api.depends('rule_id')
    # def _compute_rule_values(self):
    #     for brw_each in self:
    #         brw_each.update_rules()
    #
    # def update_rules(self):
    #     for brw_each in self:
    #         locked_edit = False
    #         locked_import = True
    #         locked_compute = True
    #         payment = False
    #         account = False
    #         if brw_each.rule_id:
    #             locked_edit = brw_each.rule_id.locked_edit
    #             locked_import = brw_each.rule_id.locked_import
    #             locked_compute = brw_each.rule_id.locked_compute
    #             payment = brw_each.rule_id.payment
    #             account = brw_each.rule_id.account
    #         brw_each.locked_edit = locked_edit
    #         brw_each.locked_import = locked_import
    #         brw_each.locked_compute = locked_compute
    #         brw_each.payment = payment
    #         brw_each.account = account
    #

    @api.model
    def get_puts_values(self, brw_payslip_puts, brw_rule):
        DEC = 2
        amount = 0.00
        for brw_line in brw_payslip_puts:
            if brw_line.rule_id == brw_rule:
                amount += brw_line.amount
        return round(amount, DEC)

    @api.model
    def get_amount_rules(self, brw_payslip_puts, brw_rule):
        amount = self.get_puts_values(brw_payslip_puts, brw_rule)
        if brw_rule.category_id.code == "IN":
            return amount, amount
        if brw_rule.category_id.code == "OUT":
            return amount, -amount
        return amount, amount

    def compute_by_selected_rule(self, brw_rule):
        self.ensure_one()
        DEC = 2
        brw_each = self
        amount, amount_factor = self.get_amount_rules(brw_each.input_line_ids, brw_rule)
        result = round(amount, DEC) != 0.00
        return result, amount, amount_factor


    def update_total(self):
        DEC=2
        total=0.00
        total_paid=0.00
        for brw_each in self:
            for brw_line in brw_each.liquidation_line_ids:
                if brw_line.type=='liquidation':
                    if brw_line.transaction_type in ('income','expense'):
                        total+=brw_line.signed_amount
            brw_each.total=round(total,DEC)
            brw_each.total_to_paid = round(total, DEC)
            brw_each.total_paid = round(total_paid, DEC)
            total_pending=total-total_paid
            brw_each.total_pending = round(total_pending, DEC)

    @api.onchange('liquidation_line_ids', 'liquidation_line_ids.signed_amount', 'liquidation_line_ids.amount' )
    def onchange_line_ids(self):
        self.update_total()

    @api.depends('liquidation_line_ids', 'liquidation_line_ids.signed_amount', 'liquidation_line_ids.amount' )
    def _compute_total(self):
        for brw_each in self:
            brw_each.update_total()

    def compute_rules(self):
        self._get_last_payslips()
        self._get_liquidation_lines()
        self.onchange_liquidation_line_ids()
        return True

    def _get_liquidation_lines(self):
        category_map = {
            self.env.ref('gps_hr.type_income').id: 'income',
            self.env.ref('gps_hr.type_expense').id: 'expense',
            self.env.ref('gps_hr.type_provision').id: 'provision',
        }
        for liquidation in self:
            if not liquidation.contract_id:
                raise ValidationError(
                    _("There's no contract set on payslip %s for %s. Check that there is at least a contract set on the employee form.",
                      liquidation.name, liquidation.employee_id.name))
            localdict = liquidation._get_localdict()
            localdict["brw_liquidation"] = liquidation
            liquidation_line_ids = [(5,)]
            rule_ids = liquidation.contract_id.contract_type_id.struct_id.struct_rule_ids
            if rule_ids:
                sequence = 1
                for brw_rule in rule_ids:
                    rule_type = category_map.get(brw_rule.category_id.id, 'unknown')
                    if not brw_rule.legal_iess:
                        continue
                    localdict["brw_rule"] = brw_rule
                    localdict["type"] = 'liquidation'
                    success_rule, amount, amount_factor = brw_rule._new_satisfy_liquidation_condition(localdict)
                    if success_rule:
                        localdict.update({
                            'amount': amount,
                            'amount_factor': amount
                        })
                        amount, result_qty, result_rate = brw_rule._new_compute_liquidation_rule(localdict)
                        liquidation_line_ids.append((0, 0, {
                            "rule_id": brw_rule.id,
                            "name": brw_rule.name,
                            "transaction_type": rule_type,
                            "amount": amount,
                            "amount_original": amount,
                            "sequence": sequence,
                            'type': 'liquidation',
                            "category_id": brw_rule.category_id.id
                        }))
                        sequence += 1
            liquidation.liquidation_line_ids=liquidation_line_ids
        return True

    def _get_last_payslips(self):
        category_map = {
            self.env.ref('gps_hr.type_income').id: 'income',
            self.env.ref('gps_hr.type_expense').id: 'expense',
            self.env.ref('gps_hr.type_provision').id: 'provision',
        }
        for liquidation in self:
            if not liquidation.contract_id:
                raise ValidationError(
                    _("There's no contract set on payslip %s for %s. Check that there is at least a contract set on the employee form.",
                      liquidation.name, liquidation.employee_id.name))
            localdict = liquidation._get_localdict()
            localdict["brw_liquidation"] = liquidation
            last_payslip_ids=[(5,)]
            rule_ids = liquidation.contract_id.contract_type_id.struct_id.struct_rule_ids
            if rule_ids:
                sequence = 1
                for brw_rule in rule_ids:
                    rule_type = category_map.get(brw_rule.category_id.id, 'unknown')
                    if brw_rule.type == 'liquidation' or not brw_rule.legal_iess:
                        continue
                    localdict["brw_rule"] = brw_rule
                    localdict["type"] = 'payslip'
                    success_rule, amount, amount_factor = brw_rule._new_satisfy_liquidation_condition(localdict)
                    if success_rule:
                        localdict.update({
                            'amount': amount,
                            'amount_factor': amount
                        })
                        amount, result_qty, result_rate = brw_rule._new_compute_liquidation_rule(localdict)
                        last_payslip_ids.append((0, 0, {
                            "rule_id": brw_rule.id,
                            "name": brw_rule.name,
                            "transaction_type": rule_type,
                            "amount":amount,
                            "amount_original": amount,
                            "sequence": sequence,
                            'type': 'payslip',
                            "category_id":brw_rule.category_id.id
                        }))
                        sequence += 1
            liquidation.last_payslip_ids=last_payslip_ids
        return True

    @api.onchange('company_id','liquidation_line_ids','liquidation_line_ids.amount','liquidation_line_ids.transaction_type')
    def onchange_liquidation_line_ids(self):
        DEC=2
        self.ensure_one()
        account_ids=[(5,)]
        for brw_liquidation_line in self.liquidation_line_ids:
            if brw_liquidation_line.amount>0:
                if brw_liquidation_line.transaction_type in ('income','expense',):
                    debit, credit = 0.00, 0.0
                    debit_provision, credit_provision = 0.00, 0.0
                    #####por provision
                    if brw_liquidation_line.rule_id.provision_rule_ids:
                        for brw_provision_payment in brw_liquidation_line.rule_id.provision_rule_ids:
                            mapped_provisions=self.last_payslip_ids.filtered(lambda x: x.rule_id==brw_provision_payment)
                            reversed_type=None
                            amount_provision=0.00
                            if brw_liquidation_line.transaction_type == 'income':
                                debit_provision = round(sum(mapped_provisions.mapped('amount')), DEC)
                                reversed_type = 'debit'
                                amount_provision=debit_provision
                            else:
                                credit_provision = round(sum(mapped_provisions.mapped('amount')), DEC)
                                reversed_type = 'credit'
                                amount_provision = credit_provision
                            ##################################################reversos######################################################
                            if reversed_type  is not None:
                                account_id = self.resolve_account(brw_liquidation_line.company_id,
                                                                  brw_provision_payment,
                                                                  amount_provision,
                                                                  reversed_type)
                                account_ids.append((0, 0, {
                                    "account_id": account_id,
                                    "debit": debit_provision,
                                    "credit": credit_provision,
                                    "rule_id": brw_liquidation_line.rule_id.id,
                                    "locked": False,
                                    "origin": "automatic"
                                }))
                                ########################################################################################################
                                if brw_liquidation_line.transaction_type == 'income':
                                    debit = round(brw_liquidation_line.amount - debit_provision, DEC)
                                    type = 'debit'
                                else:
                                    credit = round(brw_liquidation_line.amount - credit_provision, DEC)
                                    type = 'credit'
                                account_id = self.resolve_account(brw_liquidation_line.company_id,
                                                                   brw_liquidation_line.rule_id, brw_liquidation_line.amount,
                                                                  type)
                                account_ids.append((0, 0, {
                                    "account_id": account_id,
                                    "debit": debit,
                                    "credit": credit,
                                    "rule_id": brw_liquidation_line.rule_id.id,
                                    "locked": False,
                                    "origin": "automatic"
                                }))
                            ########################################################################################################
                    else:
                        if brw_liquidation_line.transaction_type=='income':
                            debit=round(brw_liquidation_line.amount,DEC)
                            type = 'debit'
                        else:
                            credit=round(brw_liquidation_line.amount,DEC)
                            type = 'credit'
                        account_id=self.resolve_account(brw_liquidation_line.company_id,brw_liquidation_line.rule_id,brw_liquidation_line.amount,type)
                        account_ids.append((0,0,{
                            "account_id":account_id,
                            "debit":debit,
                            "credit": credit,
                            "rule_id":brw_liquidation_line.rule_id.id,
                            "locked":False,
                            "origin":"automatic"
                        }))
                else:
                    srch_account = self.env["hr.salary.rule.account"].sudo().search([
                        ('rule_id', '=', brw_liquidation_line.rule_id.id),
                        ('company_id', '=', brw_liquidation_line.company_id.id),
                        ('type', '=', 'payslip'),
                    ])
                    for brw_account in srch_account:
                        if brw_account.rule_id.code=='PROV_VAC':
                            if brw_account.account_type=='debit':
                                continue
                        debit, credit = 0.00, 0.00
                        if brw_account.account_type=='debit':
                            debit=brw_liquidation_line.amount
                        else:
                            credit = brw_liquidation_line.amount
                        account_ids.append((0, 0, {
                            "account_id": brw_account.account_id.id,
                            "debit": debit,
                            "credit": credit,
                            "rule_id": brw_liquidation_line.rule_id.id,
                            "locked": False,
                            "origin": "automatic"
                        }))
        self.update_account_to_pay(account_ids)
        self.account_ids=account_ids

    @api.model
    def resolve_account(self,brw_company,brw_rule,amount,type):
        srch_account=self.env["hr.salary.rule.account"].sudo().search([
            ('rule_id','=',brw_rule.id),
            ('company_id', '=', brw_company.id),
            ('type','=','payslip'),
            ('account_type','=',type)
        ])
        if not srch_account:
            return False
        return srch_account[0].account_id.id

    def action_verified(self):
        DEC=2
        for brw_each in self:
            #brw_each.compute_rules()
            if round(brw_each.total,DEC)<0.00:
                raise ValidationError(_("El valor no puede ser menor a 0.00"))
            date_for_payment=brw_each.get_payment_dates()
            brw_each.write({"state":"verified",
                            "date_for_payment":date_for_payment,
                            "date_for_account":brw_each.date_end
                            })
        return True

    def action_sended(self):
        for brw_each in self:
            if not brw_each.date_for_payment:
                raise ValidationError(_("Debes definir una fecha para enviar a pagar "))
            if not brw_each.date_for_account:
                raise ValidationError(_("Debes definir una fecha para enviar a contabilizar "))
            brw_each.create_move()
            brw_each.action_create_request()
            brw_each.write({"state":"sended"})
            if brw_each.total<=0.00:
                brw_each.action_paid()
        return True

    def action_approved(self):
        DEC=2
        for brw_each in self:
            if round(brw_each.total,DEC)<0.00:
                raise ValidationError(_("El valor no puede ser menor a 0.00"))
            if brw_each.do_account:
                for brw_account in brw_each.account_ids:
                    if brw_account.rule_id:
                        if not brw_account.account_id:
                            raise ValidationError(_("Debes definir una cuenta para %s") % (brw_account.rule_id.name,))
                    else:
                        if not brw_account.account_id:
                            raise ValidationError(_("Debes definir una cuenta en todas las lineas de asientos") )
            if not brw_each.date_for_account:
                raise ValidationError(_("Debes definir una fecha para contabilizar "))
            brw_each.write({"state":"approved"})
            if round(brw_each.total, DEC)==round(0.00, DEC):
                brw_each.action_liquidated()
        return True

    def action_reversed_verified(self):
        for brw_each in self:
            brw_each.action_cancel_move()
            brw_each.write({"state": "verified"})
        return True

    def get_payment_dates(self):
        self.ensure_one()
        brw_each=self
        OBJ_CONFIG = self.env["account.configuration.payment"].sudo()
        brw_conf = OBJ_CONFIG.search([
            ('company_id', '=', brw_each.company_id.id)
        ])
        date_for_payment = fields.Date.context_today(self)

        x = CalendarManager()
        v = x.dow(date_for_payment)

        if brw_conf.day_id.value != v:
            date_for_payment = self.obtener_fecha_proximo_dia(date_for_payment,
                                                              brw_conf.day_id.value)
        return date_for_payment

    def obtener_fecha_proximo_dia(self, fecha_actual, dia_semana):
        while True:
            # Agregar el número de días que corresponde

            if calendarO.dow(fecha_actual) == dia_semana:
                return fecha_actual
            fecha_final = fecha_actual + timedelta(days=1)
            fecha_actual = fecha_final

    def action_paid(self):
        for brw_each in self:
            if not brw_each.date_for_payment:
                raise ValidationError(_("Debes definir una fecha para enviar a pagar "))
            brw_each.write({"state":"paid"})
        return True

    def create_move(self):
        OBJ_MOVE = self.env["account.move"]
        for brw_each in self:
            if not brw_each.do_account:
                continue
            if brw_each.move_id:
                if brw_each.move_id.state=='posted':
                    raise ValidationError(_("Ya existe un asiento publicado!!"))
            if not brw_each.company_id.payslip_journal_id:
                raise ValidationError(_("No hay diario por defecto para publicar asiento de nomina!!"))
            line_ids=[(5,)]
            vals = {
                "move_type": "entry",
                "name": "/",
                'narration': brw_each.name,
                'date': brw_each.date_for_account,
                'ref': "%s ,LIQUIDACION # %s" % (brw_each.name, brw_each.id,),
                'company_id': brw_each.company_id.id,
                'journal_id':brw_each.company_id.payslip_journal_id.id,
            }
            if not brw_each.account_ids:
                raise ValidationError(_("No hay detalle para generar el asiento "))
            for brw_line in brw_each.account_ids:
                line_ids += [(0, 0, {
                    "name":"LIQUIDACION # %s ,%s" % (brw_each.id,brw_line.account_id.name),
                    'debit': brw_line.debit,
                    'credit': brw_line.credit,
                    'ref': vals["ref"],
                    'account_id':brw_line.account_id.id,
                    'partner_id': brw_each.employee_id.partner_id.id,
                    'date': brw_each.date_for_account,
                    'liquidation_payment_id':brw_line.id,
                    #"rule_id":brw_line.rule_id.id
                })]#
            vals["line_ids"] = line_ids
            brw_move = OBJ_MOVE.create(vals)
            brw_move.action_post()
            brw_each.write({"move_id":brw_move.id})
        return True

    def action_create_request(self):

        return True



    def action_cancel(self):
        value=super().action_cancel()
        self.action_cancel_move()
        self.action_cancel_request()
        return value

    def action_cancel_request(self):

        return True

    def action_cancel_move(self):
        for brw_each in self:
            if brw_each.move_id:
                brw_each.move_id.action_cancel()
        return True

    def action_reversed_states(self):
        for brw_each in self:
            brw_each.write({"state":"sended",'payment_id':False})
        return True

    @api.constrains('contract_id', 'state')
    def _check_unique_contract_not_cancelled(self):
        for record in self:
            if record.state == 'cancelled':
                continue  # No valida si está cancelado
            domain = [
                ('id', '!=', record.id),
                ('contract_id', '=', record.contract_id.id),
                ('state', '!=', 'cancelled')
            ]
            if self.search_count(domain) > 0:
                raise ValidationError(
                    _("Ya existe una liquidación para este contrato que no está anulada.")
                )

    def sum_by_rules(self,brw_rule):
        DEC=2
        self.ensure_one()
        lines=self.input_line_ids.filtered(lambda x: x.rule_id==brw_rule)
        values = lines.mapped('original_pending')
        new_lines= self.new_input_line_ids .filtered(lambda x: x.rule_id == brw_rule)
        values+= new_lines.mapped('amount')
        amount= values and round(sum(values) ,DEC)or 0.00
        amount_factor=brw_rule.category_id.code=='IN' and 1 or -1
        return amount, amount_factor, (amount>0)

    def sum_by_provisions(self,brw_rule):
        DEC=2
        self.ensure_one()
        lines=self.provision_ids.filtered(lambda x: x.rule_id in brw_rule.provision_rule_ids)

        values=lines.mapped('amount_residual')
        amount= values and round(sum(values) ,DEC)or 0.00
        amount_factor=amount
        return amount, amount_factor, (amount>0)

    @api.onchange('last_payslip_ids')
    def onchange_last_payslip_ids(self):
        self.update_payslip_total()

    @api.depends('last_payslip_ids')
    def update_payslip_total(self):
        for brw_each in self:
            brw_each._update_payslip_total()

    def _update_payslip_total(self):
        DEC = 2
        for brw_each in self:
            total_in, total_out, total_provision, total_payslip = 0.00, 0.00, 0.00, 0.00
            for brw_line in brw_each.liquidation_line_ids:
                if brw_line.category_id.code == "PRO":
                    total_provision += brw_line.amount
                if brw_line.category_id.code == "IN":
                    total_in += brw_line.amount
                if brw_line.category_id.code == "OUT":
                    total_out += brw_line.amount
            total_payslip = total_in + total_out
            brw_each.total_in = round(total_in, DEC)
            brw_each.total_out = round(total_out, DEC)
            brw_each.total_provision = round(total_provision, DEC)
            brw_each.total_payslip = round(total_payslip, DEC)


    #########################################
    @api.onchange('liquidation_line_ids')
    def onchange_liquidation_total(self):
        self.update_liquidation_total()

    @api.depends('liquidation_line_ids')
    def _compute_liquidation_total(self):
        for brw_each in self:
            brw_each.update_liquidation_total()

    def update_liquidation_total(self):
        DEC = 2
        for brw_each in self:
            total_in_liquidation, total_out_liquidation, total_provision_liquidation, total_liquidation = 0.00, 0.00, 0.00, 0.00
            for brw_line in brw_each.liquidation_line_ids:
                if brw_line.category_id.code == "PRO":
                    total_provision_liquidation += brw_line.amount
                if brw_line.category_id.code == "IN":
                    total_in_liquidation += brw_line.amount
                if brw_line.category_id.code == "OUT":
                    total_out_liquidation += brw_line.amount
            total_liquidation = total_in_liquidation - total_out_liquidation
            brw_each.total_in_liquidation = round(total_in_liquidation, DEC)
            brw_each.total_out_liquidation = round(total_out_liquidation, DEC)
            brw_each.total_provision_liquidation = round(total_provision_liquidation, DEC)
            brw_each.total_liquidation = round(total_liquidation, DEC)

    ##########################################

    def action_liquidated(self):
        DEC=2
        for brw_each in self:
            if brw_each.do_account:
                if brw_each.state!='paid' and round(brw_each.total,DEC)>0.00:
                    raise ValidationError(_("El documento debe estar liquidado!!!"))
            else:
                if brw_each.state!='verified' and round(brw_each.total,DEC)>0.00:
                    raise ValidationError(_("El documento debe estar por verificar!!!"))
            brw_each.write({"state":"liquidated"})
            ################################################segmentp de bloqueo########################################################
            if brw_each.historic_line_ids:
                for brw_historic in brw_each.historic_line_ids:
                    brw_historic.write({"state": "liquidated"})
            if brw_each.period_ids:
                for brw_period in brw_each.period_ids:
                    if brw_period.state=='confirmed':
                        pending_days=brw_period.pending_days
                        if pending_days>0:
                            brw_period.write({"line_ids":[(0,0,{
                                "name":"LIQUIDADOS POR FINIQUITO",
                                "date":brw_each.date_process,
                                "days":pending_days,
                                'type':'payment',
                                "comments": "LIQUIDADOS EN FINIQUITO",
                                'payment_state':'validate'
                            })]})
                        brw_period.test_period()
                    #if brw_period.state=='draft':
                    #brw_period.wirte({"state":""})
            ################################################segmentp de bloqueo########################################################
        return True

    def action_draft(self):
        for brw_each in self:
            if brw_each.state!='verified':
                raise ValidationError(_("Solo puedes cambiar a estado preliminar si el estado es verificado"))
        return super().action_draft()