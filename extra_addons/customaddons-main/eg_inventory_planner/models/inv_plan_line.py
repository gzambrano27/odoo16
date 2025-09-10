from datetime import datetime

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.tools import get_lang


class PlannerReportLine(models.Model):
    _name = "inv.plan.line"
    _order = "product_id"
    _description = "Planner report line"

    product_id = fields.Many2one(comodel_name='product.product', string="Product Name")
    image_small = fields.Binary(string="Icon")
    categ_id = fields.Many2one(related="product_id.categ_id")
    supplier_id = fields.Many2one(comodel_name='res.partner', string="Supplier Name")
    unit_cost = fields.Float(string="Cost")
    sales_price = fields.Float(string="Sales Price", readonly=True)
    profit_percentage = fields.Float(string="Profit %", compute="_compute_profit_percent", store=True, readonly=True)
    need_to_order = fields.Integer(string="Forecast")
    velocity = fields.Float(string="Velocity", help="Expected Sales per day")
    available_stock = fields.Float(string="Stock", help="Available Stock = onhand - outgoing")
    # earlier incoming stock ==> new:on po
    incoming_stock = fields.Float(string="ON PO", help="Incoming Stock")
    # earlier growth multiplier ==> new:multiplier
    virtual_stock = fields.Float(string="Virtual Stock", help="Virtual Stock = onhand - outgoing + incoming")
    growth_multiplier = fields.Float(string="Multiplier", default=1.0)
    # earlier extra stock days ==> new:stock days
    extra_stock_days = fields.Integer(string="Stock Days", required=True)
    # earlier lead time ==> new:Lead Time
    lead_time = fields.Integer(string="Lead Time")
    supplier_ids = fields.Many2many(comodel_name='res.partner')
    sales_out_in = fields.Float(string="Sales Out In")
    total_cost = fields.Float(string="Total Cost", compute="_compute_profit_percent", store=True, readonly=True)
    total_profit = fields.Float(string="Total Profit", compute="_compute_profit_percent", store=True, readonly=True)
    sold_qty = fields.Float(string="Sold")
    color = fields.Selection([('none', 'None'), ('red', 'Red'), ('yellow', 'Yellow')], compute="_compute_color")
    inv_plan_id = fields.Many2one('inv.plan', string='Report')
    sub_category_ids = fields.Many2many('product.sub.category', string="Sub Categories")


    @api.depends("unit_cost", 'need_to_order')
    def _compute_profit_percent(self):
        for rec in self:
            gain = rec.product_id.list_price - rec.unit_cost
            rec.profit_percentage = (gain * 100) / rec.sales_price
            rec.total_cost = rec.unit_cost * rec.need_to_order
            rec.total_profit = gain * rec.need_to_order

    def _compute_color(self):
        icpSudo = self.env['ir.config_parameter'].sudo()
        warn_sales_out = int(icpSudo.get_param('eg_inventory_planner.warn_sales_out', default=0))
        error_sales_out = int(icpSudo.get_param('eg_inventory_planner.error_sales_out', default=0))
        for rec in self:
            if warn_sales_out >= rec.sales_out_in > error_sales_out:
                rec.color = 'yellow'
            elif rec.sales_out_in <= error_sales_out:
                rec.color = 'red'
            else:
                rec.color = "none"

    @api.onchange('extra_stock_days', 'lead_time', 'growth_multiplier', 'extra_stock_days')
    def _onchange_report_line(self):
        total_days = self.extra_stock_days + self.lead_time
        self.need_to_order = (total_days * self.velocity * self.growth_multiplier) - self.virtual_stock

    def create_purchase_order(self):
        inv_plan_id = self.mapped('inv_plan_id')
        icpSudo = self.env['ir.config_parameter'].sudo()
        auto_confirm_po = int(icpSudo.get_param('eg_inventory_planner.auto_confirm_po', default=0))
        if len(inv_plan_id) > 1:
            raise ValidationError("Something went wrong.\nHint: multiple report found.")
        if inv_plan_id.state == 'confirm':
            raise ValidationError("Purchase order already created.")
        if not inv_plan_id.state == 'approved':
            raise ValidationError("Report is yet not approved.")
        if inv_plan_id.create_date.date() != datetime.now().date():
            raise ValidationError("PO can not be created from past report.\nYou need to generate report today.")
        inv_plan_id.write({
            'state': 'confirm',
        })
        no_vendor_line_ids = self.env['inv.plan.line'].search([('id', 'in', self.ids), ('supplier_id', '=', False)])
        if no_vendor_line_ids:
            raise ValidationError("Below product do not have any supplier!!!\n{}".format(
                "\n".join(no_vendor_line_ids.mapped('product_id.display_name'))))
        supplier_ids = self.mapped('supplier_id')
        for supplier_id in supplier_ids:
            line_ids = self.env['inv.plan.line'].search([('supplier_id', '=', supplier_id.id), ('id', 'in', self.ids)])
            if not line_ids:
                continue
            purchase_order_obj = self.env['purchase.order']
            po_line_obj = self.env['purchase.order.line']
            date_now = datetime.now()
            po_vals = {
                'partner_id': supplier_id.id,
                'date_order': date_now,
                'inv_plan_id': line_ids.mapped('inv_plan_id').id,
            }
            if supplier_id.purchase_rep_id:
                po_vals.update({'user_id': supplier_id.purchase_rep_id.id})
            if supplier_id.picking_type_id:
                po_vals.update({'picking_type_id': supplier_id.picking_type_id.id})

            order_id = purchase_order_obj.create(po_vals)
            order_id.onchange_partner_id()

            for line_id in line_ids:
                if line_id.need_to_order <= 0:
                    raise ValidationError("Forecast quantity must be greater than zero.")
                order_line = po_line_obj.new({
                    'order_id': order_id.id,
                    'product_id': line_id.product_id.id,
                    'product_uom': line_id.product_id.uom_id.id,
                    'price_unit': line_id.unit_cost
                })
                order_line.onchange_product_id()
                order_line.product_qty = line_id.need_to_order
                order_line.price_unit = line_id.unit_cost
                order_line.date_planned = date_now
                order_line_values = order_line._convert_to_write(order_line._cache)
                order_line = po_line_obj.create(order_line_values)
            if auto_confirm_po:
                order_id.button_confirm()

    def write(self, vals):
        if self.mapped('inv_plan_id').state in ['confirm', 'cancel']:
            raise ValidationError("Purchase order as already created you can not edit these lines!!!")
        return super(PlannerReportLine, self).write(vals)
