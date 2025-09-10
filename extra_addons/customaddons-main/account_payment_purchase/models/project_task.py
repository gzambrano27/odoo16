# Copyright 2014 Akretion - Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2014 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, tools, _


class ProjectTask(models.Model):
    _inherit = "project.task"

    planned_date_begin = fields.Datetime('Inicio Fecha Planeada')
    planned_date_end  = fields.Datetime('Fin Fecha Planeada')
    overlap_warning = fields.Char('overlap_warning')
    user_names = fields.Char('user_names')
    allocated_hours = fields.Float('allocated_hours')