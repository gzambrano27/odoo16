# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError, UserError


class EmployeeAttendanceRaw(models.Model):
	_inherit = 'employee.attendance.raw'

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
		# Si no se proporciona un dominio, inicializamos como vacío
		domain = domain or []

		# Si el contexto tiene "only_user", no modificamos el dominio
		if not self._context.get("only_user", False):
			return super(EmployeeAttendanceRaw, self)._where_calc(domain, active_test)

		# Usuario actual
		user = self.env["res.users"].sudo().browse(self._uid)

		# Verificar si pertenece al grupo de empleados
		if user.has_group("gps_hr.group_empleados_usuarios"):
			employee = self.env["hr.employee"].sudo().search([('user_id', '=', user.id)], limit=1)

			if employee:
				# ✅ incluir al empleado y todos sus subordinados (recursivo)
				subordinates = self._get_all_subordinates(employee)
				employees_ids = employee.ids + subordinates.ids
				if not employees_ids:
					employees_ids = [-1]  # evita dominio vacío
				domain.append(("employee_id", "in", employees_ids))
			else:
				domain.append(("employee_id", "=", -1))

		# Llamar a la función original con el dominio modificado
		return super(EmployeeAttendanceRaw, self)._where_calc(domain, active_test)
