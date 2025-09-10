from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class InvPlanTmpl(models.Model):
    _name = "inv.plan.tmpl"
    _description = "Inventory Planner Template"

    name = fields.Char("Report Name")
    categ_ids = fields.Many2many('product.category', string="Product Category")
    sub_categ_ids = fields.Many2many('product.sub.category', string="Sub Category")
    extra_stock_days = fields.Integer(string="Extra Stock In Days", default=1, required=True)
    vendor_ids = fields.Many2many(comodel_name='res.partner')
    lead_time = fields.Integer(string="Lead Time")
    growth_multiplier = fields.Float(string="Growth Multiplier", default=1.0)
    velocity_manual = fields.Boolean(string="Velocity Manual")
    from_date = fields.Datetime(string="From Date")
    to_date = fields.Datetime(string="To Date")
    days = fields.Integer(string="Days")
    warehouse_ids = fields.Many2many('stock.warehouse', string="Warehouse")
    rep_line_ids = fields.One2many('inv.plan.line', 'inv_plan_id', string="Planner Line")
    state = fields.Selection(
        [('draft', 'Draft'), ('report_generated', 'Generated'), ('request', 'Requested'), ('approved', 'Approved'),
         ('confirm', 'Purchase Order'),
         ('cancel', 'Cancel')], default='draft')
    po_ids = fields.One2many('purchase.order', 'inv_plan_id', string="Purchase Order", readonly=True)
    vendor_selection = fields.Selection([('cheapest_vendor', 'Cheapest Vendor'),
                                         ('quickest_vendor', 'Quickest Vendor'),
                                         ('specific_vendor', 'Specific Vendor')], default='specific_vendor',
                                        string="Vendor Selection Strategy")
    product_sale_history_ids = fields.One2many(comodel_name='product.sale.history', inverse_name='inventory_plan_id',
                                               string="Sale Order History")
    product_purchase_history_ids = fields.One2many(comodel_name='product.purchase.history',
                                                   inverse_name='inventory_plan_id',
                                                   string="Purchase Order History")
    create_po = fields.Boolean(string='Create PO')
    duration = fields.Integer(string='Report Generate Interval', default=1)
    interval_type = fields.Selection([('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
                                     string='Interval Unit', default='days')
    generate_report = fields.Boolean(string='Auto Generate Report', default=True)
    inv_plan_ids = fields.One2many(comodel_name='inv.plan', inverse_name='auto_inv_plan_id')
    cron_id = fields.Many2one(comodel_name='ir.cron', string='Schedule Action')
    nextcall = fields.Datetime(string="Next Report Generate Date", related='cron_id.nextcall')

    @api.model
    def create(self, vals):
        res = super(InvPlanTmpl, self).create(vals)
        for rec in res:
            cron_id = self.env['ir.cron'].sudo().create({
                'user_id': self.env.ref('base.user_root').id,
                'active': True,
                'interval_type': rec.interval_type,
                'interval_number': rec.duration,
                'numbercall': -1,
                'doall': True,
                'name': rec.name,
                'model_id': self.env['ir.model']._get_id(self._name),
                'state': 'code',
                'code': 'model.auto_generate_inventory_planner(record_id={})'.format(rec.id),
            })
            rec.cron_id = cron_id.id
        return res

    def write(self, vals):
        res = super(InvPlanTmpl, self).write(vals)
        for rec in self:
            if "generate_report" in vals:
                rec.cron_id.write({'active': rec.generate_report})
            if "duration" in vals:
                rec.cron_id.write({'interval_number': rec.duration})
            if "interval_type" in vals:
                rec.cron_id.write({'interval_type': rec.interval_type})
            if "name" in vals:
                rec.cron_id.write({'name': rec.name})
        return res

    def auto_generate_inventory_planner(self, record_id=None):
        """
        Cron for auto generate inventory planner report Hourly
        :return:
        """
        auto_inv_plan_ids = self.env['inv.plan.tmpl'].search(
            [('id', '=', record_id)])
        for inv_id in auto_inv_plan_ids if auto_inv_plan_ids else self:
            inv_plan_id = self.env['inv.plan'].create({
                'extra_stock_days': inv_id.extra_stock_days,
                'lead_time': inv_id.lead_time,
                'growth_multiplier': inv_id.growth_multiplier,
                'vendor_selection': inv_id.vendor_selection,
                'vendor_ids': inv_id.vendor_ids.ids if inv_id.vendor_ids else False,
                'velocity_manual': inv_id.velocity_manual,
                'from_date': inv_id.from_date,
                'to_date': inv_id.to_date,
                'days': inv_id.days,
                'categ_ids': inv_id.categ_ids.ids if inv_id.categ_ids else False,
                'sub_categ_ids': inv_id.sub_categ_ids.ids if inv_id.sub_categ_ids else False,
                'warehouse_ids': inv_id.warehouse_ids.ids if inv_id.warehouse_ids else False,
                'auto_inv_plan_id': inv_id.id,
            })
            old_inv_ids = self.env['inv.plan'].search(
                [('auto_inv_plan_id', '=', inv_id.id), ('id', '!=', inv_plan_id.id),
                 ('state', 'in', ['draft', 'report_generated'])])
            for old_inv_id in old_inv_ids:
                old_inv_id.state = 'cancel'
            inv_plan_id.generate_planner_line()
            #     CREATE PURCHASE ORDER
            if inv_id.create_po:
                for plan_line_id in inv_id.rep_line_ids:
                    inv_id.write({
                        'state': 'confirm',
                    })
                    supplier_ids = plan_line_id.mapped('supplier_id')
                    for supplier_id in supplier_ids:
                        line_ids = self.env['inv.plan.line'].search(
                            [('supplier_id', '=', supplier_id.id), ('id', 'in', inv_plan_id.rep_line_ids.ids)])
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
                            if line_id.need_to_order > 0:
                                order_line = po_line_obj.create({
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
                                po_line_obj.write(order_line_values)

    @api.onchange('from_date', 'to_date')
    def _onchange_date(self):
        if self.from_date and self.to_date:
            date_from = self.from_date
            date_to = self.to_date
            delta = date_to - date_from
            self.days = delta.days + 1
            if self.days < 0:
                raise ValidationError("Invalid date")
