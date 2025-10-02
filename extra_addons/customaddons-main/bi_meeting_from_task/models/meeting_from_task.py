# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, timedelta


class TareaProyecto(models.Model):
    _inherit = 'project.task'

    reunion_id = fields.Many2one('calendar.event', string="Reunión", readonly=True)
    conteo_reuniones = fields.Integer('Cantidad de Reuniones', compute='_compute_reunion')

    # Contar reuniones
    @api.depends('reunion_id')
    def _compute_reunion(self):
        for x in self:
            x.conteo_reuniones = x.env['calendar.event'].search_count([('tarea_id', '=', x.id)])

    def action_ver_reuniones_tarea(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("calendar.action_calendar_event")
        return action


class EventoCalendario(models.Model):
    _inherit = 'calendar.event'

    tarea_id = fields.Many2one('project.task', string="Tarea", readonly=True)
    proyecto_id = fields.Many2one('project.project', string="Proyecto")
    conteo_tareas = fields.Integer('Cantidad de Tareas', compute='_compute_tarea')

    @api.model
    def default_get(self, fields):
        res = super(EventoCalendario, self).default_get(fields)
        # tarea = self.env.context.get('active_id')
        # if tarea:
        #     tarea_obj = self.env['project.task'].browse(tarea)
        #     tarea_obj.write({'reunion_id': self.id})
        #     res.update({'tarea_id': tarea, 'proyecto_id': tarea_obj.project_id.id})
        return res

    # Contar tareas
    @api.depends('tarea_id')
    def _compute_tarea(self):
        self.conteo_tareas = self.env['project.task'].search_count([('reunion_id', '=', self.id)])
