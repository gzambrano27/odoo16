from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from ...calendar_days.tools import CalendarManager,DateManager,MonthManager
dtObj = DateManager()

class ThFamilyBurden(models.Model):
    _inherit="th.family.burden"

    @api.model
    def _get_selection_relationship(self):
        return [('child','Hijo/Hija'),
                ('wife_husband','Conyugue'),
                ('father_mother','Padre/Madre')]

    @api.depends('birth_date')
    def _get_work_datas(self):
        for brw_each in self:
            age = 0
            if brw_each.birth_date:
                age = dtObj.years(fields.Date.context_today(self),brw_each.birth_date)
            brw_each.age = age

    genero = fields.Selection([
        ('Hombre', 'Hombre'),
        ('Mujer', 'Mujer'),
    ], 'Sexo', default='Hombre')
    age = fields.Integer(string='Edad',compute="_get_work_datas")
    birth_date=fields.Date(groups=None)


    relationship=fields.Selection(selection=_get_selection_relationship)
    @api.onchange('birth_date')
    def onchange_birth_date(self):
        age = 0
        warning={}
        if self.birth_date is not None and self.birth_date:
            if self.birth_date > fields.Date.context_today(self):
                warning={"title": _("Error"), "message": _(
                    "Fecha de Nacimiento no puede ser mayor  a la fecha actual")}
            age = dtObj.years(fields.Date.context_today(self), self.birth_date)
        self.age=age
        if warning:
            return {"warning":warning}

    @api.onchange('name')
    def onchange_name(self):
        self.name = self.name and self.name.upper() or None

    @api.model
    def _where_calc(self, domain, active_test=True):
        # Si no se proporciona un dominio, inicializamos como vacío
        domain = domain or []

        # Si el contexto tiene "only_user", no modificamos el dominio
        if not self._context.get("only_user", False):
            return super(ThFamilyBurden, self)._where_calc(domain, active_test)

        # Obtener el usuario actual
        user = self.env["res.users"].sudo().browse(self._uid)

        # Comprobar si el usuario tiene permisos de grupo 'group_empleados_usuarios'
        if user.has_group("gps_hr.group_empleados_usuarios"):
            # Buscar el empleado relacionado con el usuario
            employee = self.env["hr.employee"].sudo().search([('user_id', '=', user.id)], limit=1)

            # Si encontramos un empleado, modificamos el dominio para filtrar por su ID
            if employee:
                domain.append(("employee_id", "in", tuple(employee.ids + [-1, -1])))
            else:
                domain.append(("employee_id", "=", -1))
        # Llamar a la función original con el dominio modificado
        return super(ThFamilyBurden, self)._where_calc(domain, active_test)

