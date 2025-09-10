from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    velocity_days = fields.Integer(string="Velocity Days", default_model='stock.picking')
    warn_sales_out = fields.Integer(string="Yellow Sales Out Days", default_model='stock.picking')
    error_sales_out = fields.Integer(string="Red Sales Out Days", default_model='stock.picking')
    auto_confirm_po = fields.Integer(string="Auto Confirm PO", default_model='stock.picking')

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        icpSudo = self.env['ir.config_parameter'].sudo()
        res.update(
            velocity_days=int(icpSudo.get_param('eg_inventory_planner.velocity_days', default=0)),
            warn_sales_out=int(icpSudo.get_param('eg_inventory_planner.warn_sales_out', default=0)),
            error_sales_out=int(icpSudo.get_param('eg_inventory_planner.error_sales_out', default=0)),
            auto_confirm_po=int(icpSudo.get_param('eg_inventory_planner.auto_confirm_po', default=0)),
        )
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        icpSudo = self.env['ir.config_parameter'].sudo()
        icpSudo.set_param("eg_inventory_planner.velocity_days", self.velocity_days)
        icpSudo.set_param('eg_inventory_planner.warn_sales_out', self.warn_sales_out)
        icpSudo.set_param('eg_inventory_planner.error_sales_out', self.error_sales_out)
        icpSudo.set_param('eg_inventory_planner.auto_confirm_po', self.auto_confirm_po)
        return res
