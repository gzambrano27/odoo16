from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class PlannerReport(models.Model):
    _name = "inv.plan"
    _description = "Inventory Plan"

    name = fields.Char("Name", default="New", copy=False)
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
    state = fields.Selection([('draft', 'Draft'), ('report_generated', 'Generated'), ('request', 'Requested'), ('approved', 'Approved'),
         ('confirm', 'Purchase Order'),
         ('cancel', 'Cancel')], default='draft',string='Status')
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
    auto_inv_plan_id = fields.Many2one(comodel_name='inv.plan.tmpl', string='Auto Plan')

    @api.onchange('from_date', 'to_date')
    def _onchange_date(self):
        if self.from_date and self.to_date:
            date_from = self.from_date
            date_to = self.to_date
            delta = date_to - date_from
            self.days = delta.days + 1
            if self.days < 0:
                raise ValidationError("Invalid date")

    def generate_planner_line(self):
        if self.name == _('New'):
            self.name = self.env['ir.sequence'].next_by_code('inv.plan') or _('New')
        if not self.extra_stock_days:
            raise ValidationError("Extra stock in days must be > 0 !!!")

        if self.days < 0:
            raise ValidationError("Invalid date in velocity ")

        if not self.growth_multiplier:
            raise ValidationError("Growth multiplier must be > 0 !!!")

        if self.velocity_manual:
            if not self.from_date or not self.to_date:
                raise ValidationError("Enter velocity date")

            if self.to_date <= self.from_date:
                raise UserError("Enter To date greater than From date")

        domain = [('purchase_ok', '=', True), ('type', '=', 'product')]

        if self.categ_ids:
            domain += [('categ_id', 'child_of', self.categ_ids.ids)]

        if self.sub_categ_ids:
            domain += [('sub_categ_ids', 'child_of', self.sub_categ_ids.ids)]

        if self.vendor_selection == 'specific_vendor':
            if self.vendor_ids:
                #supplierinfo_ids = self.env['product.supplierinfo'].search([('id', 'in', self.vendor_ids.ids)])
                supplierinfo_ids = self.env['product.supplierinfo'].search([('partner_id', 'in', self.vendor_ids.ids)])
                product_tmpl_ids = supplierinfo_ids.mapped('product_tmpl_id')
                domain += [('id', 'in', product_tmpl_ids.ids)]
                if not product_tmpl_ids:
                    raise ValidationError("No product found for selected Vendors")

        product_tmpl_ids = self.env['product.template'].search(domain)
        if not product_tmpl_ids:
            raise ValidationError("No product found for selected Filters")

        if self.velocity_manual:
            date_from = self.from_date
            date_to = self.to_date
            delta = date_to - date_from
            days = delta.days + 1
        else:
            icpSudo = self.env['ir.config_parameter'].sudo()
            days = int(icpSudo.get_param('eg_inventory_planner.velocity_days', default=1))
            date_to = datetime.now()
            date_from = date_to - timedelta(days=days - 1)
            if not days:
                raise ValidationError(
                    "Please configure Velocity days in configuration if you are not using manual Velocity duration.")
        warehouse_conditon = ""

        if self.warehouse_ids:
            warehouse_conditon = "and SO.warehouse_id in ({})".format(
                ",".join(map(str, self.warehouse_ids.ids)))
        for product_tmpl_id in product_tmpl_ids:
            if product_tmpl_id.last_published_date:
                delta = date_to - product_tmpl_id.last_published_date
                new_days = delta.days + 1
                if new_days < days:
                    days = new_days
            for product_id in product_tmpl_id.product_variant_ids:
                lead_time_list = []
                product_cost_list = []
                for seller_id in product_id.seller_ids:
                    lead_time_list.append(seller_id.delay)
                    product_cost_list.append(seller_id.price)
                if self.vendor_selection == "cheapest_vendor":
                    cheapest_price = min(product_cost_list) if product_cost_list else 0
                    supplier_id = product_id.seller_ids.filtered(lambda l: l.price == cheapest_price)
                    supplier_id = supplier_id[0] if len(supplier_id) > 1 else supplier_id
                elif self.vendor_selection == "quickest_vendor":
                    lead_time = min(lead_time_list) if lead_time_list else 0
                    supplier_id = product_id.seller_ids.filtered(lambda l: l.delay == lead_time)
                    supplier_id = supplier_id[0] if len(supplier_id) > 1 else supplier_id
                else:
                    supplier_id = product_id.seller_ids[0] if product_id.seller_ids else self.env[
                        'product.supplierinfo']

                max_order_sale = []
                order_qty = 0
                sale_line_ids = self.env["sale.order.line"].search([
                    ("order_id.create_date", ">=", date_from),
                    ("order_id.create_date", "<=", date_to),
                    ("product_id", "=", product_id.id),
                ])
                for sale_line_id in sale_line_ids:
                    order_qty += sale_line_id.product_uom_qty
                    max_order_sale.append(sale_line_id.product_uom_qty)
                total_sale = len(sale_line_ids.mapped("order_id"))
                avg_sale = total_sale / days
                max_order_purchase = []
                purchase_order_qty = 0
                purchase_line_ids = self.env["purchase.order.line"].search([
                    ("order_id.create_date", ">=", date_from),
                    ("order_id.create_date", "<=", date_to),
                    ("product_id", "=", product_id.id),
                ])
                for purchase_line_id in purchase_line_ids:
                    purchase_order_qty += purchase_line_id.product_qty
                    max_order_purchase.append(purchase_line_id.product_qty)
                total_purchase = len(purchase_line_ids.mapped("order_id"))
                avg_purchase = total_purchase / days

                #supplierinfo_line_id = product_id.seller_ids.filtered(lambda l: l.product_id.id == product_id.id)
                supplierinfo_line_id = product_id.seller_ids.filtered(lambda l: l.product_tmpl_id.id == product_id.id)
                if not supplierinfo_line_id:
                    supplierinfo_line_id = product_id.seller_ids.filtered(
                        lambda l: l.product_tmpl_id.id == product_tmpl_id.id and not l.product_id)
                if supplierinfo_line_id and not supplierinfo_line_id[0].id:
                    continue
                order_line_query = """
                select COALESCE(sum(SOL.product_uom_qty),0) from sale_order_line SOL join sale_order SO on SOL.order_id=SO.id 
                    where SO.date_order >= '%s'
                        and SO.date_order <= '%s' 
                        and SOL.product_id = %d 
                        and SO.state != 'cancel'
                """ % (
                    date_from.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    date_to.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    product_id.id)
                if self.warehouse_ids:
                    order_line_query += warehouse_conditon
                try:
                    self._cr.execute(order_line_query)
                except:
                    self._cr.execute()
                query_res = self._cr.fetchall()

                if not query_res[0][0]:
                    continue
                lead_time = supplier_id.delay if supplier_id else self.lead_time
                ordered_qty = query_res[0][0]
                sales_velocity = ordered_qty / days
                total_days = self.extra_stock_days + lead_time
                supplier_list = []
                available_stock = product_id.qty_available - product_id.outgoing_qty
                virtual_stock = product_id.virtual_available
                need_to_order = (total_days * sales_velocity * self.growth_multiplier) - virtual_stock
                sales_out_in = virtual_stock / sales_velocity

                for seller_id in product_id.seller_ids:
                    supplier_list.append(seller_id.id)
                if need_to_order > 0:
                    line = self.env["inv.plan.line"].create({
                        'product_id': product_id.id,
                        'unit_cost': supplier_id.price if supplier_id else 0,
                        'sales_price': product_id.list_price,
                        'supplier_id': supplier_id.id if supplier_id else False,
                        'available_stock': available_stock,
                        'need_to_order': int(need_to_order),
                        'velocity': sales_velocity,
                        'sold_qty': ordered_qty,
                        'incoming_stock': product_id.incoming_qty,
                        'extra_stock_days': self.extra_stock_days,
                        'lead_time': lead_time,
                        'growth_multiplier': self.growth_multiplier,
                        'image_small': product_id.image_128,
                        'sales_out_in': sales_out_in,
                        'virtual_stock': virtual_stock,
                        'inv_plan_id': self.id,
                        'sub_category_ids': product_id.sub_categ_ids.ids,
                    })
                    line.supplier_ids = supplier_list

                self.env["product.sale.history"].create({
                    'inventory_plan_id': self.id,
                    'from_date': date_from.date(),
                    'to_date': date_to.date(),
                    'duration_in_day': days,
                    'product_id': product_id.id,
                    'quantity': order_qty,
                    'total_sale_order': total_sale,
                    'average_daily_sale': avg_sale,
                    'maximum_daily_sale_qty': max(max_order_sale) if max_order_sale else 0,
                })

                self.env["product.purchase.history"].create({
                    'inventory_plan_id': self.id,
                    'from_date': date_from.date(),
                    'to_date': date_to.date(),
                    'duration_in_day': days,
                    'product_id': product_id.id,
                    'quantity': purchase_order_qty,
                    'total_purchase_order': total_purchase,
                    'average_daily_purchase': avg_purchase,
                    'maximum_daily_purchase_qty': max(max_order_purchase) if max_order_purchase else 0,
                })

            self.write({
                'state': 'report_generated',
            })
        if self.user_has_groups('eg_inventory_planner.group_planner_manager'):
            self.action_approved()
        action = self.env.ref('eg_inventory_planner.action_inv_plan_line').read()[0]
        action['domain'] = [('inv_plan_id', '=', self.id)]
        return action

    def open_report_lines(self):
        action = self.env.ref('eg_inventory_planner.action_inv_plan_line').read()[0]
        action['domain'] = [('inv_plan_id', '=', self.id)]
        return action

    def action_request(self):
        self.write({
            'state': 'request',
        })

    def action_approved(self):
        self.write(({
            'state': 'approved',
        }))

    def action_cancel(self):
        self.po_ids.button_cancel()
        self.write({
            'state': 'cancel',
        })
