# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from odoo.exceptions import ValidationError,UserError
from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit="res.partner"

    def action_open_employees(self):
        # if self.user_has_groups('gps_hr.group_datos_limitados_empleados_rrhh'):
        #     raise ValidationError(_("No tienes acceso para ver datos del empleado"))
        return super().action_open_employees()