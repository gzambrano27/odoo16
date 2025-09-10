from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, timedelta

class ActasActa(models.Model):
    _inherit = 'actas.acta'

    def siguiente_dia_laborable(self):
        hoy = date.today()
        dia = hoy + timedelta(days=1)  # empezar con el día siguiente

        # Si cae sábado (5) o domingo (6), saltamos
        while dia.weekday() >= 5:  # 5 = sábado, 6 = domingo
            dia += timedelta(days=1)

        return dia

    @api.model
    def get_current_employee(self):
        user = self.env["res.users"].sudo().browse(self._uid)
        employee=self.env["hr.employee"]
        # Comprobar si el usuario tiene permisos de grupo 'group_empleados_usuarios'
        if user.has_group("gps_hr.group_empleados_usuarios"):
            # Buscar el empleado relacionado con el usuario
            employee = self.env["hr.employee"].sudo().search([('user_id', '=', user.id)], limit=1)
        return employee

    @api.model
    def _get_default_employee_ids(self):
        employee=self.get_current_employee()
        if employee:
            brw_parent= employee.sudo().parent_id
            return brw_parent and brw_parent.id or False
        return False

    @api.model
    def _get_default_computer_models(self):
        employee = self.get_current_employee()
        l = [(5,)]
        if employee:
            actas = self.env["actas.acta"].sudo().search([('create_uid', '=', self._uid)], limit=1,order="id desc")
            last_acta=actas
            if last_acta.computer_models:
               for brw_modelo in  last_acta.computer_models:
                   l.append((0,0,{
                       "model":brw_modelo.model,
                       "brand": brw_modelo.brand,
                       "serial_number": brw_modelo.serial_number,
                       "color": brw_modelo.color,
                   }))
        return l

    @api.model
    def _get_default_personnel(self):
        employee = self.get_current_employee()
        if employee:
            return [(5,),(0,0,{
                "employee_id":employee.id
            })]
        return [(5,)]

    fecha_recepcion_equipo = fields.Date(string='Fecha de Recepción de Equipo',default=siguiente_dia_laborable)
    employee_ids = fields.Many2one('hr.employee', string='Empleados',default=_get_default_employee_ids)
    computer_models = fields.One2many('actas.computer', 'acta_id', string='Modelos',default=_get_default_computer_models)
    personnel = fields.One2many('actas.personnel', 'acta_id', string='Personal',default=_get_default_personnel)

    @api.model
    def _where_calc(self, domain, active_test=True):
        # Si no se proporciona un dominio, inicializamos como vacío
        domain = domain or []

        # Si el contexto tiene "only_user", no modificamos el dominio
        if not self._context.get("only_user", False):
            return super(ActasActa, self)._where_calc(domain, active_test)

        # Obtener el usuario actual
        user = self.env["res.users"].sudo().browse(self._uid)

        # Comprobar si el usuario tiene permisos de grupo 'group_empleados_usuarios'
        if user.has_group("gps_hr.group_empleados_usuarios"):
            # Buscar el empleado relacionado con el usuario
            documents = self.env["actas.personnel"].sudo().search([('employee_id.user_id', '=', user.id)], limit=1)

            # Si encontramos un empleado, modificamos el dominio para filtrar por su ID
            if documents:
                documents_ids=documents.mapped('acta_id').ids
                domain.append(("id", "in", tuple(documents_ids + [-1, -1])))
            else:
                domain.append(("id", "=", -1))
        # Llamar a la función original con el dominio modificado
        return super(ActasActa, self)._where_calc(domain, active_test)