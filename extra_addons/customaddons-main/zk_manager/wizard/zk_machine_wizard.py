# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models,_
import logging
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


class ZkMachineWizard(models.Model):
    _name = "zk.machine.wizard"
    _description="Asistente para Biometricos"


    biometric_id=fields.Many2one("zk.machine","Biometrico")
    employee_id=fields.Many2one("hr.employee","Empleado")
    name=fields.Char("Nombre en Biometrico")
    device_id_num = fields.Char("Biometric Device ID")

    type = fields.Selection([('create_user', 'Crear Usuario'),
                             ('update_user', 'Actualizar Usuario'),
                             ('delete_user', 'Borrar Usuario'),
                             ], string="Tipo", default="create_user")
    lock_biometric = fields.Boolean(related="biometric_id.lock_biometric", store=False, readonly=True)

    type_update = fields.Selection([('only_name', 'Nombre'),
                                    ('only_password', 'Contraseña'),
                                    ('only_fingerprint', 'Huella')
                                    ], string="Actualizar", default="only_name")
    password = fields.Char("Contraseña", size=4)

    hand = fields.Selection([('left', 'Izquierda'), ('right', 'Derecha')], string="Mano", default="right")
    right_finger = fields.Selection(
        [
            ('1', 'Pulgar'),
            ('2', 'Índice'),
            ('3', 'Medio'),
            ('4', 'Anular'),
            ('5', 'Meñique'),
        ],
        string='Dedo de la Mano Derecha',
        required=True,
        help="Selecciona el dedo correspondiente para esta huella.", default='2'
    )
    left_finger = fields.Selection(
        [
            ('5', 'Meñique'),
            ('4', 'Anular'),
            ('3', 'Medio'),
            ('2', 'Índice'),
            ('1', 'Pulgar'),
        ],
        string='Dedo de la Mano Izquierda',
        required=True,
        help="Selecciona el dedo correspondiente para esta huella.", default='2'
    )
    register_employee_ids = fields.Many2many("hr.employee", "details_wizard_employee_rel", "wizard_id", "employee_id",
                                             "Empleados", required=False, compute="compute_register_employee_ids")

    @api.depends('biometric_id')
    @api.onchange('biometric_id')
    def compute_register_employee_ids(self):
        for brw_each in self:
            register_employee_ids = brw_each.biometric_id.employee_ids.mapped('employee_id')

            brw_each.register_employee_ids = register_employee_ids

    @api.constrains('password')
    def _check_password_is_numeric(self):
        for record in self:
            if record.type == "update_user" and record.type_update == "only_password":
                if not record.password.isdigit():
                    raise ValidationError("La contraseña debe contener solo números")

    @api.constrains('device_id_num')
    def _check_device_id_num_is_numeric(self):
        for record in self:
            if not record.device_id_num.isdigit():
                raise ValidationError("El ID Biométrico debe contener solo números")
            if not record.device_id_num or int(record.device_id_num) <= 0:
                raise ValidationError(_("Debes definir un ID Biométrico y debe ser mayor a 0"))

    def process(self):
        for brw_each in self:
            device_id_num = int(brw_each.device_id_num)
            if brw_each.type == "create_user":
                brw_each.biometric_id.create_user(device_id_num, brw_each.employee_id)
                brw_employee= brw_each.employee_id.with_context(bypass_partner_restriction=True)
                brw_employee.write({"device_id_num": device_id_num})
            if brw_each.type == "delete_user":
                brw_each.biometric_id.delete_user(device_id_num)
                brw_employee = brw_each.employee_id.with_context(bypass_partner_restriction=True)
                brw_employee.write({"device_id_num": None})
            if brw_each.type == "update_user":
                if brw_each.type_update == "only_name":
                    brw_each.biometric_id.update_user(device_id_num, brw_each.employee_id)
                if brw_each.type_update == "only_password":
                    brw_each.biometric_id.update_user(device_id_num, brw_each.employee_id,
                                                      password=str(brw_each.password))
                if brw_each.type_update == "only_fingerprint":
                    factor_hand = 1 if brw_each.hand == 'left' else 2
                    # Selección del dedo correspondiente según la mano
                    if brw_each.hand == 'left':
                        finger = int(brw_each.left_finger) - 1  # Restamos 1 para que los dedos sean del 0 al 4
                    else:
                        finger = int(brw_each.right_finger) - 1  # Lo mismo para la mano derecha
                    # Ahora, la variable `finger` tiene un valor entre 0 y 4
                    # Si la API espera valores de dedo en el rango de 0-9, debes asegurarte de no exceder ese rango
                    if finger > 9:
                        raise ValueError("El valor del dedo está fuera del rango permitido (0-9).")
                    value_finger = (factor_hand * finger)
                    brw_each.biometric_id.take_fingerprint(device_id_num, brw_each.employee_id, value_finger)
            brw_each.biometric_id.recover_users()
        return True

    @api.onchange('employee_id')
    def onchange_emploee_id(self):
        if self.employee_id:
            self.name = self.employee_id.clean_name()
            self.password = str(self.employee_id.id)
            if self.lock_biometric:
                self.device_id_num = str(self.employee_id.id)
