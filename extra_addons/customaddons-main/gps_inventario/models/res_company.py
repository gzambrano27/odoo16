# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from odoo.exceptions import ValidationError,UserError
from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit="res.company"

    transit_location_id=fields.Many2one("stock.location","Ubicación")