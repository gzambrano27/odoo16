from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _default_picking_type(self):
        return self._get_picking_type(self.env.context.get('company_id') or self.env.company.id)

    picking_type_id = fields.Many2one('stock.picking.type', 'Input Location', required=True,
                                      default=_default_picking_type,
                                      domain="[('code','=','incoming')]",
                                      help="Input Location for this Vendor.",
                                      groups="stock.group_stock_manager")
    purchase_rep_id = fields.Many2one(comodel_name="res.users", string="Purchase Representative",
                                      groups="purchase.group_purchase_manager")

    @api.model
    def _get_picking_type(self, company_id):
        picking_type = self.env['stock.picking.type'].search(
            [('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company_id)])
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search(
                [('code', '=', 'incoming'), ('warehouse_id', '=', False)])
        return picking_type[:1]
