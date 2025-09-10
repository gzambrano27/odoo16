from odoo import api, fields, models, tools, netsvc, _


class res_partner(models.Model):
    _inherit = 'res.partner'

    employee = fields.Boolean('Es empleado')
    