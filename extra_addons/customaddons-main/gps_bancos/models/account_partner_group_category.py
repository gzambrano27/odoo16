# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime


class AccountGroupReport(models.Model):
    _name = 'account.partner.group.category'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Grupo de Clientes"

    code=fields.Char("Codigo",required=True,tracking=True)
    name = fields.Char("Descripcion ", required=True,tracking=True)
    partner_ids=fields.One2many("res.partner","group_category_id","Clientes",tracking=True)

    _rec_name="code"