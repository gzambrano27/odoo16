# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models,_
from odoo.exceptions import UserError,ValidationError
import logging
_logger = logging.getLogger(__name__)




class EmployeeAttendanceRaw(models.Model):
    _name = 'employee.attendance.raw'
    _description = 'Marcaciones del Empleado'
    _order = 'date_time desc'

    employee_id = fields.Many2one('hr.employee', string='Empleado')
    date_time = fields.Datetime(string='Fecha y Hora de Marcación')
    biometric_id = fields.Many2one('zk.machine', string='Dispositivo Biométrico')
    raw_user_id = fields.Char(string='ID Usuario en Biométrico')
    imported = fields.Boolean(string="Importado a asistencia", default=False)