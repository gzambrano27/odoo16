# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models,_
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

from ..tools.Zk import ZkManager


class BiometricDeviceDetailsEmployee(models.Model):
    _name = "zk.machine.employee"
    _description="Empleados de un biometrico"

    device_id=fields.Many2one("zk.machine",on_delete="cascade")
    employee_id = fields.Many2one("hr.employee", "Empleado", required=False)
    name = fields.Char("Nombre en Biométrico")
    device_id_num = fields.Char("ID Biométrico")
    password = fields.Char("Contraseña", size=4)

    has_password = fields.Boolean("Tiene Contraseña", compute="_compute_has_password")

    fid0 = fields.Boolean("Meñique I.")
    fid1 = fields.Boolean("Anular I.")
    fid2 = fields.Boolean("Medio I.")
    fid3 = fields.Boolean("Índice I.")
    fid4 = fields.Boolean("Pulgar I.")

    fid5 = fields.Boolean("Pulgar D.")
    fid6 = fields.Boolean("Índice D.")
    fid7 = fields.Boolean("Medio D.")
    fid8 = fields.Boolean("Anular D.")
    fid9 = fields.Boolean("Meñique D.")

    def _compute_has_password(self):
        for brw_each in self:
            has_password = (brw_each.password and len(brw_each.password) > 0)
            brw_each.has_password = has_password

    def action_update_user(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Actualizar Usuario',
            'view_mode': 'form',
            'res_model': 'zk.machine.wizard',
            'domain': [],
            'context': {"default_employee_id": self.employee_id.id,
                        "default_biometric_id": self.device_id.id,
                        "default_device_id_num": self.device_id_num,
                        "default_name": self.name,
                        'default_type': "update_user",
                        "default_password": self.password
                        },
            'target': 'new',  # Puede ser 'new', 'current' o 'inline'
        }

    def action_delete_user(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Borrar Usuario',
            'view_mode': 'form',
            'res_model': 'zk.machine.wizard',
            'domain': [],
            'context': {"default_employee_id": self.employee_id.id,
                        "default_biometric_id": self.device_id.id,
                        "default_device_id_num": self.device_id_num,
                        "default_name": self.name,
                        'default_type': "delete_user"

                        },
            'target': 'new',  # Puede ser 'new', 'current' o 'inline'
        }