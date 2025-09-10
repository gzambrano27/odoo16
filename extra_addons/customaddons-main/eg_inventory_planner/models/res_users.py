from odoo import models, fields


class ResUsers(models.Model):
    _inherit = "res.users"

    res_partner_ids = fields.One2many(comodel_name="res.partner", inverse_name="purchase_rep_id", string="Vendors")
