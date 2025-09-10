import dateutil.parser

from odoo import api, fields, models


def check_gantt_date(value):
    if isinstance(value, str):
        return dateutil.parser.parse(value, ignoretz=True)
    else:
        return value


class ProjectTask(models.Model):
    _inherit = "project.task"  # pylint: disable=R8180

    priority = fields.Selection([
        ('0', 'Baja'),
        ('1', 'Media'),
        ('2', 'Alta'),
    ], default='1', index=True, string="Prioridad", tracking=True)

    duration = fields.Integer(string="Duration (days)", default=-1)
    duration_unit = fields.Char(default="d")

    costo = fields.Float(string="Costo", default=0.0)
    cantidad = fields.Integer(string="Cantidad", default=0)

    percent_done = fields.Integer(string="Done %", default=0, compute="_compute_percent_done", store=True)

    @api.depends('progress')
    def _compute_percent_done(self):
        for record in self:
            record.percent_done = int(round(record.progress))

    parent_index = fields.Integer(default=0)

    assigned_ids = fields.Many2many(
        "res.users", relation="assigned_resources", string="Assigned resources"
    )
    assigned_resources = fields.One2many(
        "project.task.assignment", inverse_name="task", string="Assignments"
    )
    baselines = fields.One2many("project.task.baseline", inverse_name="task")

    segments = fields.One2many("project.task.segment", inverse_name="task")

    effort = fields.Integer(string="Effort (hours)", default=0)

    gantt_calendar_flex = fields.Char(string="Gantt Calendar Ids")
    linked_ids = fields.One2many(
        "project.task.linked", inverse_name="to_id", string="Linked"
    )
    scheduling_mode = fields.Selection(
        [
            ("Normal", "Normal"),
            ("FixedDuration", "Fixed Duration"),
            ("FixedEffort", "Fixed Effort"),
            ("FixedUnits", "Fixed Units"),
        ],
    )
    constraint_type = fields.Selection(
        [
            ("assoonaspossible", "As soon as possible"),
            ("aslateaspossible", "As late as possible"),
            ("muststarton", "Must start on"),
            ("mustfinishon", "Must finish on"),
            ("startnoearlierthan", "Start no earlier than"),
            ("startnolaterthan", "Start no later than"),
            ("finishnoearlierthan", "Finish no earlier than"),
            ("finishnolaterthan", "Finish no later than"),
        ],
    )
    constraint_date = fields.Datetime()
    effort_driven = fields.Boolean(default=False)
    manually_scheduled = fields.Boolean(default=False)
    bryntum_rollup = fields.Boolean(string="Rollup", default=False)
    wbs_value = fields.Char(string="WBS Value")

    employee_ids = fields.Many2many(
        "hr.employee",
        string="Employees",
        compute="_compute_employee_ids",
        inverse="_inverse_employee_ids",
        search="_search_employee_ids",
        store=False,
    )

    assigned_employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        string="Assigned Employees",
        compute="_compute_assigned_employees",
        store=True
    )

    is_assigned_to_my_team = fields.Boolean(
        string="Assigned to my team",
        compute="_compute_is_assigned_to_my_team",
        store=False
    )

    @api.depends_context('uid')
    @api.depends('assigned_employee_ids.parent_id')
    def _compute_is_assigned_to_my_team(self):
        user = self.env.user
        employee = user.employee_id
        if not employee:
            for task in self:
                task.is_assigned_to_my_team = False
            return

        team_employee_ids = employee.child_ids.ids  # subordinados directos
        for task in self:
            task.is_assigned_to_my_team = any(
                emp.id in team_employee_ids for emp in task.assigned_employee_ids
            )

    @api.depends("assigned_resources.resource_base")
    def _compute_assigned_employees(self):
        for task in self:
            # Filtrar empleados cuyo resource_id esté en los resource_base de las asignaciones
            resource_ids = task.assigned_resources.mapped("resource_base.id")
            employees = self.env["hr.employee"].search([("resource_id", "in", resource_ids)])
            task.assigned_employee_ids = employees

    @api.onchange("employee_ids")
    def _onchange_employee_ids(self):
        # Actualiza user_ids inmediatamente sin necesidad de guardar
        self.user_ids = self.employee_ids.mapped("user_id")

    @api.depends("assigned_resources")
    def _compute_employee_ids(self):
        for this in self:
            resources = this.assigned_resources.mapped("resource_base")
            employees = self.env["hr.employee"].search(
                [("resource_id", "in", resources.ids)]
            )
            this.employee_ids = employees

    def _inverse_employee_ids(self):
        for this in self:
            new_resources_emp = this.employee_ids.mapped("resource_id")
            old_resources_all = this.assigned_resources.mapped("resource_base")
            old_resources_emp = (
                self.env["hr.employee"]
                .search([("resource_id", "in", old_resources_all.ids)])
                .mapped("resource_id")
            )
            res_to_add = set(new_resources_emp.ids).difference(
                set(old_resources_emp.ids)
            )
            res_to_unlink = set(old_resources_emp.ids).difference(
                set(new_resources_emp.ids)
            )
            ass_to_delete = this.assigned_resources.filtered(
                lambda a: a.resource_base.id in res_to_unlink
            ).ids
            this.assigned_resources = [(2, _id) for _id in list(ass_to_delete)] + [
                (0, False, {"units": 100, "resource_base": _id})
                for _id in list(res_to_add)
            ]

    @api.model
    def _search_employee_ids(self, operator, value):
        employees = self.env["hr.employee"].search([("name", operator, value)])
        resources = employees.mapped("resource_id")
        return [("assigned_resources.resource_base", "in", resources.ids)]

    @api.returns("self", lambda value: value.id)
    def copy(self, default=None):
        task_copy = super(ProjectTask, self).copy(default)
        task_mapping = self.env.context.get("task_mapping_keys", {})
        task_mapping[self.id] = task_copy.id
        return task_copy

    @api.onchange("constraint_type")
    def _onchange_constraint_type(self):
        if not self.constraint_type:
            self.constraint_date = None
        else:
            self.constraint_date = {
                "assoonaspossible": self.planned_date_begin,
                "aslateaspossible": self.planned_date_end,
                "muststarton": self.planned_date_begin,
                "mustfinishon": self.planned_date_end,
                "startnoearlierthan": self.planned_date_begin,
                "startnolaterthan": self.planned_date_begin,
                "finishnoearlierthan": self.planned_date_end,
                "finishnolaterthan": self.planned_date_end,
            }[self.constraint_type]

    planned_date_begin = fields.Datetime("Start date")
    planned_date_end = fields.Datetime("End date")

    # Agregar el campo de alerta (tipo char) a la tarea
    alerta = fields.Char(string="Alerta", compute="_compute_alerta", store=True)

    @api.depends('planned_date_end', 'percent_done')
    def _compute_alerta(self):
        for task in self:
            mensaje = ""
            if task.percent_done >= 100:
                mensaje = "Completada"
            elif task.planned_date_end:
                end_date = (
                    fields.Datetime.from_string(task.planned_date_end)
                    if isinstance(task.planned_date_end, str)
                    else task.planned_date_end
                )
                ahora = fields.Datetime.now()
                dias_restantes = (end_date - ahora).days

                if dias_restantes > 7:
                    mensaje = "En curso"
                elif dias_restantes < 0:
                    mensaje = "Vencida"
                elif dias_restantes == 0:
                    mensaje = f"Hoy ({task.percent_done}%)"
                elif dias_restantes == 1:
                    if task.percent_done < 60:
                        mensaje = f"1 día: Crítico ({task.percent_done}%)"
                    elif task.percent_done < 80:
                        mensaje = f"1 día: Acelera ({task.percent_done}%)"
                    else:
                        mensaje = f"1 día: Finaliza ({task.percent_done}%)"
                elif dias_restantes == 2:
                    if task.percent_done < 60:
                        mensaje = f"2 días: Crítico ({task.percent_done}%)"
                    elif task.percent_done < 80:
                        mensaje = f"2 días: Insuf. ({task.percent_done}%)"
                    elif task.percent_done < 90:
                        mensaje = f"2 días: Moderado ({task.percent_done}%)"
                    else:
                        mensaje = f"2 días: Casi ok ({task.percent_done}%)"
                elif dias_restantes in [3, 4]:
                    if task.percent_done < 60:
                        mensaje = f"{dias_restantes} días: Muy bajo ({task.percent_done}%)"
                    elif task.percent_done < 80:
                        mensaje = f"{dias_restantes} días: Bajo ({task.percent_done}%)"
                    elif task.percent_done < 90:
                        mensaje = f"{dias_restantes} días: Moderado ({task.percent_done}%)"
                    else:
                        mensaje = f"{dias_restantes} días: Casi ok ({task.percent_done}%)"
                elif dias_restantes in [5, 6, 7]:
                    if task.percent_done < 60:
                        mensaje = f"{dias_restantes} días: Insuf. ({task.percent_done}%)"
                    elif task.percent_done < 80:
                        mensaje = f"{dias_restantes} días: Bajo ({task.percent_done}%)"
                    elif task.percent_done < 90:
                        mensaje = f"{dias_restantes} días: Moderado ({task.percent_done}%)"
                    else:
                        mensaje = f"{dias_restantes} días: Casi ok ({task.percent_done}%)"
            task.alerta = mensaje

    # Campo para almacenar el color de la alerta (solo danger, warning y success)
    alerta_color = fields.Char(string="Alerta Color", compute="_compute_alerta_color", store=True)

    @api.depends('alerta')
    def _compute_alerta_color(self):
        for task in self:
            if task.alerta == "Completada":
                task.alerta_color = 'success'
            elif task.alerta == "Vencida":
                task.alerta_color = 'danger'
            elif "Crítico" in task.alerta or "Insuf." in task.alerta or "Muy bajo" in task.alerta:
                task.alerta_color = 'danger'
            elif "Bajo" in task.alerta or "Acelera" in task.alerta:
                task.alerta_color = 'warning'
            elif "Finaliza" in task.alerta or "Casi ok" in task.alerta:
                task.alerta_color = 'success'
            elif "Moderado" in task.alerta or "En curso" in task.alerta or "Hoy" in task.alerta:
                task.alerta_color = 'warning'
            else:
                task.alerta_color = 'warning'

    analityc_account = fields.Many2many(
        "account.analytic.account",
        string="Cuenta analítica",
        domain="['|', ('company_id', '=', company_id), ('company_id', '=', False)]"
    )

    department_id = fields.Many2one(
        'hr.department',
        string="Departamento",
        help="Selecciona el departamento relacionado"
    )

    _sql_constraints = [
        (
            "planned_dates_check",
            "CHECK ((planned_date_begin <= planned_date_end))",
            "The planned start date must be prior to the planned end date.",
        ),
    ]

    def _read_start_date(self, default_date):
        _date = None
        if self.planned_date_begin and self.planned_date_end:
            _date = min(self.planned_date_begin, self.planned_date_end)
        elif self.planned_date_begin and not self.planned_date_end:
            _date = self.planned_date_begin
        elif self.planned_date_end and not self.planned_date_begin:
            _date = self.planned_date_end
        else:
            _date = default_date
        return _date

    def _read_end_date(self, default_date):
        _date = None
        if self.planned_date_begin and self.planned_date_end:
            _date = max(self.planned_date_begin, self.planned_date_end)
        elif self.planned_date_begin and not self.planned_date_end:
            _date = self.planned_date_begin
        elif self.planned_date_end and not self.planned_date_begin:
            _date = self.planned_date_end
        else:
            _date = default_date
        return _date
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('gantt_calendar_flex'):
                vals['gantt_calendar_flex'] = 'general'
        return super(ProjectTask, self).create(vals_list)


class ProjectTaskLinked(models.Model):
    _name = "project.task.linked"
    _description = "Project Task Linked"

    from_id = fields.Many2one("project.task", ondelete="cascade", string="From")
    to_id = fields.Many2one("project.task", ondelete="cascade", string="To")
    lag = fields.Integer(default=0)
    lag_unit = fields.Char(default="d")
    type = fields.Integer(default=2)
    dep_active = fields.Boolean(string="Active", default=True)


class ProjectTaskAssignmentUser(models.Model):
    _name = "project.task.assignment"
    _description = "Project Task User Assignment"

    task = fields.Many2one("project.task", ondelete="cascade")
    resource = fields.Many2one("res.users", ondelete="cascade", string="User")
    resource_base = fields.Many2one(
        "resource.resource", ondelete="cascade", string="Resource"
    )
    units = fields.Integer(default=0)


class ProjectTaskBaseline(models.Model):
    _name = "project.task.baseline"
    _description = "Project Task User Assignment"

    task = fields.Many2one("project.task", ondelete="cascade")
    name = fields.Char(default="")
    planned_date_begin = fields.Datetime("Start date")
    planned_date_end = fields.Datetime("End date")


class ProjectTaskSegment(models.Model):
    _name = "project.task.segment"
    _description = "Project Task Segment"

    task = fields.Many2one("project.task", ondelete="cascade")
    name = fields.Char(default="")
    planned_date_begin = fields.Datetime("Start date")
    planned_date_end = fields.Datetime("End date")
