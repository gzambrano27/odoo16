

from odoo import models, fields, api, _

class ResUsers(models.Model):
    _inherit = 'res.users'

    employee = fields.Boolean(default=True)

    # @api.onchange('initial_origin')
    # def onchange_initial_origin(self):
    #     if self.initial_origin:
    #         partner_ids = self.env['res.partner'].search([('id', 'in', self.mapped('partner_id.id'))])
    #         for partner in partner_ids:
    #             partner.onchange_initial_origin(self.initial_origin)

    # @api.onchange('vat', 'origin')
    # def vat_change(self):
    #     if self.origin or self.vat:
    #         partner_ids = self.env['res.partner'].search([('id', 'in', self.mapped('partner_id.id'))])
    #         for partner in partner_ids:
    #             partner.vat_change(self.origin, self.vat)

# No es necesario llamar explícitamente a la clase al final
