# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError,UserError

class HrEmployee(models.Model):
    _inherit="hr.employee"

    actas_ids = fields.One2many('maintenance.acta', 'empleado_recibe', string='Actas', groups='maintenance.group_equipment_manager',
                domain=[('state', '=', 'open')],  # Filtra solo actas activas
                                )