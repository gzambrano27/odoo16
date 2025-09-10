# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class TlArea(models.Model):
    _name = 'th.area'
    _description = 'Area for the human resource'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    description = fields.Text(string='Description')
    parent_id = fields.Many2one('th.area', string='Parent Area')
    child_ids = fields.One2many('th.area', 'parent_id', string='Child Areas')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    active = fields.Boolean(string='Active', default=True)

    @api.model
    def create(self, vals):
        if 'company_id' not in vals:
            vals['company_id'] = self.env.company.id
        return super(TlArea, self).create(vals)

    def write(self, vals):
        if 'company_id' in vals:
            for area in self:
                if area.company_id != vals['company_id']:
                    raise UserError(_('You cannot change the company of an area.'))
        return super(TlArea, self).write(vals)