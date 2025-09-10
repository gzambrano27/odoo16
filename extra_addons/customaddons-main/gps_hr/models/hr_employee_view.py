from odoo import models, fields, api
from odoo.exceptions import ValidationError

class HrEmployeeView(models.Model):
    _name = 'hr.employee.view'
    _description = 'Vista de Empleados'
    _auto = False

    id = fields.Integer(string="ID", readonly=True)
    employee_id = fields.Char(  string="ID Biométrico ", readonly=True)
    employee_name = fields.Char(string="Empleado", readonly=True)

    def init(self):
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW hr_employee_view AS (
                   select id,id::varchar as employee_id,name as employee_name from hr_employee
                   where active=true
            )
        """)

    _order="id desc"

    @api.model
    def _where_calc(self, domain, active_test=True):
        # Si no se proporciona un dominio, inicializamos como vacío
        domain = domain or []

        # Si el contexto tiene "only_user", no modificamos el dominio
        if not self._context.get("only_user", False):
            return super(HrEmployeeView, self)._where_calc(domain, active_test)

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
        return super(HrEmployeeView, self)._where_calc(domain, active_test)