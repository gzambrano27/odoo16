# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    request_acceptance_id = fields.Many2one('request.acceptance', string='Requisicion Aceptada')
    
class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    request_acceptance_line_id = fields.Many2one('request.acceptance.line ', string='Requisicion Aceptada')