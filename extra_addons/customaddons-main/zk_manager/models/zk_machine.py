# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models,_
from odoo.exceptions import UserError,ValidationError
import logging
_logger = logging.getLogger(__name__)
from ..tools.Zk import ZkManager,NO_JOBS,ERROR,COMMIT,NO_HANDLED
from ..tools.Zk import SUPERUSER_ID as ZK_SUPERUSER_ID



class ZkMachine(models.Model):
    _inherit = "zk.machine"

    @api.model
    def _get_default_lock_biometric(self):
        param_lock_biometric = self.env['ir.config_parameter'].sudo().get_param('lock.biometric.device.id',
                                                                                "False")
        return param_lock_biometric in ("1", "True")

    employee_ids=fields.One2many("zk.machine.employee","device_id","Empleado")

    lock_biometric = fields.Boolean("Bloquear ID Biométrico", compute="_compute_lock_biometric",
                                    default=_get_default_lock_biometric)

    def _compute_lock_biometric(self):
        for brw_each in self:
            lock_biometric = self._get_default_lock_biometric()
            brw_each.lock_biometric = lock_biometric

    def create_user(self, device_id_num, brw_employee):
        self.ensure_one()
        zk = ZkManager(self.name, port=self.port_no)
        v = zk.create_user(device_id_num, brw_employee.clean_name(),
                           privilege=0, password=str(brw_employee.id).zfill(4),
                           group_id='', user_id=str(brw_employee.id), card=0)
        if v.get('status', NO_JOBS) != COMMIT:
            raise ValidationError(v.get('message', "No se pudo ejecutar la acción"))
        return self.__show_message("Usuario creado exitosamente", type="success")

    def update_user(self, device_id_num, brw_employee, password=False):
        self.ensure_one()
        zk = ZkManager(self.name, port=self.port_no)
        v = zk.write_user(device_id_num, brw_employee.clean_name(),
                          privilege=0, password=password,
                          group_id='', card=0)
        if v.get('status', NO_JOBS) != COMMIT:
            raise ValidationError(v.get('message', "No se pudo ejecutar la acción"))
        return self.__show_message("Usuario actualizado exitosamente", type="success")

    def delete_user(self, device_id_num):
        self.ensure_one()
        if type(device_id_num) == str:
            device_id_num = int(device_id_num)
        zk = ZkManager(self.name, port=self.port_no)
        v = zk.delete_user(device_id_num)
        if v.get('status', NO_JOBS) != COMMIT:
            raise ValidationError(v.get('message', "No se pudo ejecutar la acción"))
        return self.__show_message("Usuario eliminado exitosamente", type="success")

    def recover_users(self):
        employee = self.env["hr.employee"].sudo()
        is_searched_by_id = employee._get_default_lock_biometric()
        for brw_each in self:
            zk = ZkManager(brw_each.name, port=brw_each.port_no)
            v = zk.get_full_users()
            if v.get("status", 0) != 2:
                raise ValidationError(_("La respuesta del Biométrico no es la correcta %s") % (v.get("message", ''),))
            users = v.get("users", {})
            employee_ids = [(5,)]
            if users:
                for each_users_ky in users:
                    user = users[each_users_ky]
                    print(user["user"].name, user["user"].password)
                    domain = [('device_id_num', '=', each_users_ky)]
                    if is_searched_by_id:
                        domain = [('id', '=', each_users_ky)]
                    srch_employee = employee.search(domain)
                    user_values = {
                        "name": user["user"].name,
                        "device_id_num": str(each_users_ky),
                        "employee_id": srch_employee and srch_employee[0].id or False,
                        "password": user["user"].password
                    }
                    fingers = user["fingers"]
                    for each_finger in fingers:
                        each_finger_ky = "fid%s" % (each_finger.fid)
                        user_values[each_finger_ky] = True
                    employee_ids.append((0, 0, user_values))
            brw_each.write({"employee_ids": employee_ids})
        return self.__show_message("Información recuperada exitosamente", type="success")

    def read_user(self, brw_employee):
        self.ensure_one()
        zk = ZkManager(self.name, port=self.port_no)
        v = zk.get_user_info(brw_employee.id)
        if v.get('status', NO_JOBS) != COMMIT:
            raise ValidationError(v.get('message', "No se pudo recuperar la información"))
        return self.__show_message("Información recuperada exitosamente", type="success")

    def take_fingerprint(self, device_id_num, brw_employee, fid):
        if type(fid) == str:
            fid = int(fid)
        self.ensure_one()
        zk = ZkManager(self.name, port=self.port_no)
        v = zk.take_fingerprint(device_id_num, fid, warning=False)
        if v.get('status', NO_JOBS) != COMMIT:
            raise ValidationError(v.get('message', "No se pudo ejecutar la acción"))
        return self.__show_message("Huellas registradas correctamente", type="success")

    def action_create_user(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Crear Usuario',
            'view_mode': 'form',
            'res_model': 'zk.machine.wizard',
            'domain': [],
            'context': {"default_employee_id": False,
                        "default_biometric_id": self.id,
                        "default_device_id_num": None,
                        "default_name": None,
                        'default_type': "create_user",
                        "default_password": None
                        },
            'target': 'new',  # Puede ser 'new', 'current' o 'inline'
        }

    @api.model
    def __show_message(self, message, type="success"):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': type,
                'sticky': False
            }
        }

    def action_test_connection(self):
        self.ensure_one()
        zk = ZkManager(self.name, port=self.port_no)
        v = zk.get_device_info()
        if v.get('status', NO_JOBS) != COMMIT:
            raise ValidationError(v.get('message', "No se pudo recuperar la información"))
        return self.__show_message("Información recuperada exitosamente: %s" % (v.get('info','')), type="success")

