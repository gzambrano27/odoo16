# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.populate import compute
import io
import base64
import xlsxwriter

_STATES = [
    ("draft", "Draft"),
    ("to_approve", "To be approved"),
    ("approved", "Approved"),
    ("in_progress", "In progress"),
    ("done", "Done"),
    ("rejected", "Rejected"),
]


class PurchaseRequestLine(models.Model):

    _name = "purchase.request.line"
    _description = "Purchase Request Line"
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _order = "id desc"

    name = fields.Char(string="Description", tracking=True)
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="UoM",
        tracking=True,
        domain="[('category_id', '=', product_uom_category_id)]",
    )
    product_uom_category_id = fields.Many2one(related="product_id.uom_id.category_id")
    product_qty = fields.Float(
        string="Quantity", tracking=True, digits="Product Unit of Measure"
    )

    referencia_anterior_po = fields.Char(related='product_id.referencia_anterior', string='Referencia Anterior')
    product_brand_id = fields.Many2one(
        "product.brand",
        string="Marca",
        help="Select a brand for this product",
        store=True
    )
    product_categ_id = fields.Many2one(
        "product.category",
        string="Categoria",
        help="Selecciona una categoria del producto",
        store=True
    )
    request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="Purchase Request",
        ondelete="cascade",
        readonly=True,
        index=True,
        auto_join=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="request_id.company_id",
        string="Company",
        store=True,
    )
    requested_by = fields.Many2one(
        comodel_name="res.users",
        related="request_id.requested_by",
        string="Requested by",
        store=True,
    )
    assigned_to = fields.Many2one(
        comodel_name="res.users",
        related="request_id.assigned_to",
        string="Assigned to",
        store=True,
    )
    date_start = fields.Date(related="request_id.date_start", store=True)
    description = fields.Text(
        related="request_id.description",
        string="PR Description",
        store=True,
        readonly=False,
    )
    origin = fields.Char(
        related="request_id.origin", string="Source Document", store=True
    )
    date_required = fields.Date(
        string="Request Date",
        required=True,
        tracking=True,
        default=fields.Date.context_today,
    )
    is_editable = fields.Boolean(compute="_compute_is_editable", readonly=True)
    is_editable_assigned_to = fields.Boolean(compute="_compute_is_editable_assigned_to", readonly=True)
    specifications = fields.Text()
    request_state = fields.Selection(
        string="Request state",
        related="request_id.state",
        store=True,
    )
    supplier_id = fields.Many2one(
        comodel_name="res.partner",
        string="Preferred supplier",
        compute="_compute_supplier_id",
        compute_sudo=True,
        store=True,
    )
    cancelled = fields.Boolean(default=False, copy=False)

    purchased_qty = fields.Float(
        string="RFQ/PO Qty",
        digits="Product Unit of Measure",
        compute="_compute_purchased_qty",
        store=True
    )
    purchase_lines = fields.Many2many(
        comodel_name="purchase.order.line",
        relation="purchase_request_purchase_order_line_rel",
        column1="purchase_request_line_id",
        column2="purchase_order_line_id",
        string="Purchase Order Lines",
        readonly=True,
        copy=False,
    )
    purchase_state = fields.Selection(
        compute="_compute_purchase_state",
        string="Purchase Status",
        selection=lambda self: self.env["purchase.order"]._fields["state"].selection,
        store=True,
    )
    move_dest_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="created_purchase_request_line_id",
        string="Downstream Moves",
    )

    orderpoint_id = fields.Many2one(
        comodel_name="stock.warehouse.orderpoint", string="Orderpoint"
    )
    purchase_request_allocation_ids = fields.One2many(
        comodel_name="purchase.request.allocation",
        inverse_name="purchase_request_line_id",
        string="Purchase Request Allocation",
    )

    employees_ids = fields.Many2many(
        comodel_name="hr.employee",
        #relation="purchase_request_employee_rel",
        #column1="purchase_request_line_id",
        #column2="employee_id",
        string="Employees",
    )

    qty_in_progress = fields.Float(
        digits="Product Unit of Measure",
        readonly=True,
        compute="_compute_qty",
        store=True,
        help="Quantity in progress.",
    )
    qty_done = fields.Float(
        digits="Product Unit of Measure",
        readonly=True,
        compute="_compute_qty",
        store=True,
        help="Quantity completed",
    )
    qty_cancelled = fields.Float(
        digits="Product Unit of Measure",
        readonly=True,
        compute="_compute_qty_cancelled",
        store=True,
        help="Quantity cancelled",
    )
    qty_to_buy = fields.Boolean(
        compute="_compute_qty_to_buy",
        string="There is some pending qty to buy",
        store=True,
    )
    pending_qty_to_receive = fields.Float(
        compute="_compute_qty_to_buy",
        digits="Product Unit of Measure",
        copy=False,
        string="Pending Qty to Receive",
        store=True,
    )
    estimated_cost = fields.Monetary(
        currency_field="currency_id",
        default=0.0,
        help="Estimated cost of Purchase Request Line, not propagated to PO.",
    )
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        domain=[("purchase_ok", "=", True)],
        tracking=True,
    )

    qty_available = fields.Float(
        string="Stock Disponible",
        compute="_compute_stock_info",
        store=True
    )

    location_name = fields.Char(
        string="Ubicación Principal",
        compute="_compute_stock_info",
        store=False
    )
    main_location_qty = fields.Float(
        string="Stock en Bodega Principal",
        compute="_compute_stock_info",
        store=False,
    )

    other_locations_qty = fields.Float(
        string="Stock en Otras Bodegas",
        compute="_compute_stock_info",
        store=False,
    )
    stock_other_company_qty = fields.Float(
        string="Stock ImportGreen",
        compute="_compute_other_company_stock",
        store=False,
    )
    un_solo_custodio = fields.Boolean('Un Custodio?')
    display_type = fields.Selection([
        ('line_section', "Sección"),
        ('line_note', "Nota"),
    ], string="Tipo de Línea", default = False, help="Define si esta línea es una sección o una nota.")
    sequence = fields.Integer(string='Sequence', default=10)
    analytic_account_names = fields.Char(
        string='Cuentas Analíticas',
        compute='_compute_analytic_account_names',
        store = True
    )
    tipo_costo = fields.Char('Tipo Costo')
    rubro = fields.Char('Rubro')
    costo_uni_apu = fields.Float('Costo U. APU',digits=(16,4))
    request_type = fields.Selection(
        related="request_id.request_type",
        string="Tipo Requisicion",
        store=True,
    )

    @api.depends('analytic_distribution')
    def _compute_analytic_account_names(self):
        for line in self:
            if isinstance(line.analytic_distribution, dict):
                # Obtiene los IDs de las cuentas analíticas
                analytic_account_ids = list(line.analytic_distribution.keys())
                # Busca los nombres de las cuentas analíticas utilizando esos IDs
                analytic_accounts = self.env['account.analytic.account'].search([('id', 'in', analytic_account_ids)])
                line.analytic_account_names = ', '.join(analytic_accounts.mapped('name'))
            else:
                line.analytic_account_names = ''

    _sql_constraints = [
            ('non_accountable_null_fields',
                "CHECK(display_type IS NULL OR (product_id IS NULL AND uom IS NULL))",
                "Forbidden values on non-accountable purchase order line"),
            ('accountable_required_fields',
                "CHECK(display_type IS NOT NULL OR (product_id IS NOT NULL AND uom IS NOT NULL))",
                "Missing required fields on accountable purchase order line."),
        ]

    @api.onchange('un_solo_custodio')
    def _onchange_un_solo_custodio(self):
        if self.un_solo_custodio:
            if not (self.product_id.categ_id.asset_fixed_control or self.product_id.categ_id.asset_fixed_depreciable):
                self.employees_ids = False
                self.un_solo_custodio = False
        else:
            self.employees_ids = False

    def _compute_other_company_stock(self):
        for line in self:
            if not line.product_id:
                line.stock_other_company_qty = 0.0
                continue
            quants = self.env['stock.quant'].with_company(2).sudo().search([
                ('product_id', '=', line.product_id.id),
                ('location_id.usage', '=', 'internal'),
            ])
            qty = sum(quants.mapped('quantity'))
            line.stock_other_company_qty = qty

    def _compute_stock_info(self):
        for line in self:
            if not line.product_id or not line.company_id:
                line.qty_available = 0.0
                line.location_name = False
                line.main_location_qty = 0.0
                line.other_locations_qty = 0.0
                continue

            product = line.product_id
            company_id = line.company_id.id

            # Buscar ubicación PRINCIPAL de esta compañía
            principal_location = self.env['stock.location'].search([
                ('usage', '=', 'internal'),
                ('company_id', '=', company_id),
                ('comment', '=', 'PRINCIPAL'),
            ], limit=1)

            # Stock en bodega principal
            main_qty = 0.0
            if principal_location:
                main_qty = sum(self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('location_id', '=', principal_location.id),
                ]).mapped('quantity'))

            # Stock en otras bodegas internas de la misma compañía (excepto PRINCIPAL)
            other_quants = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('location_id.usage', '=', 'internal'),
                ('location_id.company_id', '=', company_id),
                ('location_id.id', '!=', principal_location.id if principal_location else 0),
            ])
            other_qty = sum(other_quants.mapped('quantity'))

            # Asignar valores
            line.qty_available = main_qty + other_qty
            line.main_location_qty = main_qty
            line.other_locations_qty = other_qty
            line.location_name = principal_location.display_name if principal_location else ''
            
    # def _compute_stock_info(self):
    #     for line in self:
    #         if not line.product_id:
    #             line.qty_available = 0.0
    #             line.location_name = False
    #             continue
    #         product = line.product_id.with_context(company_id=line.company_id.id)
    #         line.qty_available =  product.qty_available  #product.virtual_available
    #         location = self.env['stock.quant'].search([
    #             ('product_id', '=', product.id),
    #             ('quantity', '>', 0),
    #             ('location_id.usage', '=', 'internal'),
    #             ('company_id', '=', line.company_id.id)
    #         ], order='quantity desc', limit=1).location_id
    #         line.location_name = location.display_name if location else ''

    @api.onchange('product_id', 'company_id')
    def _onchange_stock_info(self):
        self._compute_stock_info()

    @api.depends(
        "purchase_request_allocation_ids",
        "purchase_request_allocation_ids.stock_move_id.state",
        "purchase_request_allocation_ids.stock_move_id",
        "purchase_request_allocation_ids.purchase_line_id",
        "purchase_request_allocation_ids.purchase_line_id.state",
        "request_id.state",
        "product_qty",
    )
    def _compute_qty_to_buy(self):
        for pr in self:
            qty_to_buy = sum(pr.mapped("product_qty")) - sum(pr.mapped("qty_done"))
            pr.qty_to_buy = qty_to_buy > 0.0
            pr.pending_qty_to_receive = qty_to_buy

    @api.depends(
        "purchase_request_allocation_ids",
        "purchase_request_allocation_ids.stock_move_id.state",
        "purchase_request_allocation_ids.stock_move_id",
        "purchase_request_allocation_ids.purchase_line_id.state",
        "purchase_request_allocation_ids.purchase_line_id",
    )
    def _compute_qty(self):
        for request in self:
            done_qty = sum(
                request.purchase_request_allocation_ids.mapped("allocated_product_qty")
            )
            open_qty = sum(
                request.purchase_request_allocation_ids.mapped("open_product_qty")
            )
            request.qty_done = done_qty
            request.qty_in_progress = open_qty

    @api.depends(
        "purchase_request_allocation_ids",
        "purchase_request_allocation_ids.stock_move_id.state",
        "purchase_request_allocation_ids.stock_move_id",
        "purchase_request_allocation_ids.purchase_line_id.order_id.state",
        "purchase_request_allocation_ids.purchase_line_id",
    )
    def _compute_qty_cancelled(self):
        for request in self:
            if request.product_id.type != "service":
                qty_cancelled = sum(
                    request.mapped("purchase_request_allocation_ids.stock_move_id")
                    .filtered(lambda sm: sm.state == "cancel")
                    .mapped("product_qty")
                )
            else:
                qty_cancelled = sum(
                    request.mapped("purchase_request_allocation_ids.purchase_line_id")
                    .filtered(lambda sm: sm.state == "cancel")
                    .mapped("product_qty")
                )
                # done this way as i cannot track what was received before
                # cancelled the purchase order
                qty_cancelled -= request.qty_done
            if request.product_uom_id:
                request.qty_cancelled = (
                    max(
                        0,
                        request.product_id.uom_id._compute_quantity(
                            qty_cancelled, request.product_uom_id
                        ),
                    )
                    if request.purchase_request_allocation_ids
                    else 0
                )
            else:
                request.qty_cancelled = qty_cancelled

    @api.depends(
        "purchase_lines",
        "request_id.state",
    )
    def _compute_is_editable(self):
        for rec in self:
            if rec.request_id.state in (
                "to_approve",
                "approved",
                "rejected",
                "in_progress",
                "done",
            ):
                rec.is_editable = False
            else:
                rec.is_editable = True
        for rec in self.filtered(lambda p: p.purchase_lines):
            rec.is_editable = False

    @api.depends(
        "purchase_lines",
        "request_id.state",
    )
    def _compute_is_editable_assigned_to(self):
        for rec in self:
            if rec.request_id.state in (
                "rejected",
                #"in_progress",
                "done",
            ):
                rec.is_editable_assigned_to = False
            else:
                rec.is_editable_assigned_to = True
        for rec in self.filtered(lambda p: p.purchase_lines):
            rec.is_editable_assigned_to = False

    @api.depends("product_id", "product_id.seller_ids")
    def _compute_supplier_id(self):
        for rec in self:
            sellers = rec.product_id.seller_ids.filtered(
                lambda si, rec=rec: not si.company_id or si.company_id == rec.company_id
            )
            rec.supplier_id = sellers[0].partner_id if sellers else False

    @api.onchange("product_id")
    def onchange_product_id(self):
        if self.product_id:
            name = self.product_id.name
            if self.product_id.code:
                name = "[{}] {}".format(self.product_id.code, name)
                self.product_brand_id = self.product_id.product_tmpl_id.product_brand_id.id
                self.product_categ_id = self.product_id.product_tmpl_id.categ_id.id
            if self.product_id.description_purchase:
                name += "\n" + self.product_id.description_purchase
            self.product_uom_id = self.product_id.uom_id.id
            self.product_qty = 1
            self.name = name

    def do_cancel(self):
        """Actions to perform when cancelling a purchase request line."""
        self.write({"cancelled": True})

    def do_uncancel(self):
        """Actions to perform when uncancelling a purchase request line."""
        self.write({"cancelled": False})

    def write(self, vals):
        if "product_id" in vals and "analytic_distribution" not in vals:
            for line in self:
                if line.request_id and line.request_id.analytic_distribution:
                    vals.setdefault("analytic_distribution", line.request_id.analytic_distribution)
        res = super(PurchaseRequestLine, self).write(vals)
        if vals.get("cancelled"):
            requests = self.mapped("request_id")
            requests.check_auto_reject()
        return res
    
    @api.model
    def create(self, vals_list):
        """ Ajusta la secuencia para que cada nueva línea tenga un número único """
        if isinstance(vals_list, dict):
            vals_list = [vals_list]  # Convertir en lista si es un solo diccionario

        for values in vals_list:
            if 'sequence' not in values or values['sequence'] == 10:
                values['sequence'] = self._get_next_sequence(values.get('request_id'))
        #nuevo
        for vals in vals_list:
            if not vals.get("analytic_distribution"):
                request = self.env["purchase.request"].browse(vals.get("request_id"))
                if request and request.analytic_distribution:
                    vals["analytic_distribution"] = request.analytic_distribution
        return super(PurchaseRequestLine, self).create(vals_list)
    
    # @api.model
    # def search(self, args, **kwargs):
    #     """Elimina el filtro oculto que impide mostrar `line_section` y `line_note` en la vista."""
    #     print("ANTES DE FILTRAR ARGS:", args)  # 🔹 Depuración antes de modificar los argumentos
    #     new_args = [arg for arg in args if arg != ('display_type', '=', False)]
    #     new_args.append(('display_type', 'in', [False, 'line_section', 'line_note']))
    #     return super(PurchaseRequestLine, self).search(new_args, **kwargs)

    def _get_next_sequence(self, request_id):
        """ Busca la siguiente secuencia disponible para la requisición """
        last_line = self.search([('request_id', '=', request_id)], order="sequence desc", limit=1)
        return last_line.sequence + 1 if last_line else 10

    @api.depends(
        "purchase_lines",
        "request_id.state",
    )
    def _compute_purchased_qty(self):
        for rec in self:
            rec.purchased_qty = 0.0
            for line in rec.purchase_lines.filtered(lambda x: x.state != "cancel"):
                if rec.product_uom_id and line.product_uom != rec.product_uom_id:
                    rec.purchased_qty += line.product_uom._compute_quantity(
                        line.product_qty, rec.product_uom_id
                    )
                else:
                    rec.purchased_qty += line.product_qty

    @api.depends("purchase_lines.state", "purchase_lines.order_id.state")
    def _compute_purchase_state(self):
        for rec in self:
            temp_purchase_state = False
            if rec.purchase_lines:
                if any(po_line.state == "done" for po_line in rec.purchase_lines):
                    temp_purchase_state = "done"
                elif all(po_line.state == "cancel" for po_line in rec.purchase_lines):
                    temp_purchase_state = "cancel"
                elif any(po_line.state == "purchase" for po_line in rec.purchase_lines):
                    temp_purchase_state = "purchase"
                elif any(
                    po_line.state == "to approve" for po_line in rec.purchase_lines
                ):
                    temp_purchase_state = "to approve"
                elif any(po_line.state == "sent" for po_line in rec.purchase_lines):
                    temp_purchase_state = "sent"
                elif all(
                    po_line.state in ("draft", "cancel")
                    for po_line in rec.purchase_lines
                ):
                    temp_purchase_state = "draft"
            rec.purchase_state = temp_purchase_state

    @api.model
    def _get_supplier_min_qty(self, product, partner_id=False):
        seller_min_qty = 0.0
        if partner_id:
            seller = product.seller_ids.filtered(
                lambda r: r.partner_id == partner_id
            ).sorted(key=lambda r: r.min_qty)
        else:
            seller = product.seller_ids.sorted(key=lambda r: r.min_qty)
        if seller:
            seller_min_qty = seller[0].min_qty
        return seller_min_qty

    @api.model
    def _calc_new_qty(self, request_line, po_line=None, new_pr_line=False):
        purchase_uom = po_line.product_uom or request_line.product_id.uom_po_id
        # TODO: Not implemented yet.
        #  Make sure we use the minimum quantity of the partner corresponding
        #  to the PO. This does not apply in case of dropshipping
        supplierinfo_min_qty = 0.0
        if not po_line.order_id.dest_address_id:
            supplierinfo_min_qty = self._get_supplier_min_qty(
                po_line.product_id, po_line.order_id.partner_id
            )

        rl_qty = 0.0
        # Recompute quantity by adding existing running procurements.
        if new_pr_line:
            rl_qty = po_line.product_uom_qty
        else:
            for prl in po_line.purchase_request_lines:
                for alloc in prl.purchase_request_allocation_ids:
                    rl_qty += alloc.product_uom_id._compute_quantity(
                        alloc.requested_product_uom_qty, purchase_uom
                    )
        qty = max(rl_qty, supplierinfo_min_qty)
        return qty

    def _can_be_deleted(self):
        self.ensure_one()
        return self.request_state == "draft"

    def unlink(self):
        if self.mapped("purchase_lines"):
            raise UserError(
                _("You cannot delete a record that refers to purchase lines!")
            )
        for line in self:
            if not line._can_be_deleted():
                raise UserError(
                    _(
                        "You can only delete a purchase request line "
                        "if the purchase request is in draft state."
                    )
                )
        return super(PurchaseRequestLine, self).unlink()

    def action_show_details(self):
        self.ensure_one()
        view = self.env.ref("purchase_request.view_purchase_request_line_details")
        return {
            "name": _("Detailed Line"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "purchase.request.line",
            "views": [(view.id, "form")],
            "view_id": view.id,
            "target": "new",
            "res_id": self.id,
            "context": dict(
                self.env.context,
            ),
        }
    
    def action_export_custom(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("Requisiciones")

        headers = [
            "Codigo",
            "Descripción",
            "Cantidad",
            "UdM",
            "Requisición de compra",
            "Estado requisición",
            "Fecha de solicitud",
            "Fecha de llegada de requisicion",
            "Orden de compra",
            
            "Fecha de llegada prevista",
            "Fecha de llegada",
            "Estado de Compra",
            "Referencia Anterior",
            "Marca",
            "Cant. Realizada",
            "Stock Disponible",
            "Requerido por",
        ]
        for col, header in enumerate(headers):
            sheet.write(0, col, header)

        state_map = {
            'draft': 'Borrador',
            'in_progress': 'En Progreso',
            'approved': 'Aprobado',
            'done': 'Realizado',
            'cancel': 'Cancelado',
        }

        row = 1
        for line in self:#.search([('request_id', '=', 1792),('product_id', '=', 6525)]):
            sheet.write(row, 0, line.product_id.default_code or "")
            sheet.write(row, 1, line.product_id.name or "")
            sheet.write(row, 2, line.product_qty or 0)
            sheet.write(row, 3, line.product_uom_id.name or "")
            sheet.write(row, 4, line.request_id.name or "")
            sheet.write(row, 5, state_map.get(line.request_id.state, line.request_id.state))
            sheet.write(row, 6, str(line.request_id.date_start or ""))

            # Buscar relación entre requisición y OC
            self.env.cr.execute("""
                SELECT purchase_order_line_id 
                FROM purchase_request_purchase_order_line_rel
                WHERE purchase_request_line_id = %s
            """, (line.id,))
            rels = self.env.cr.fetchall()

            order_name = ""
            purchase_state = ""
            fecha_campo = ""
            fecha_bodega = ""
            fecha_dt = None
            fecha_arrivo = ""
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'align': 'left'})
            if rels:
                for (pol_id,) in rels:
                    pol = self.env['purchase.order.line'].browse(pol_id)
                    if pol and pol.order_id:
                        order_name = pol.order_id.name
                        purchase_state = pol.order_id.state

                        # Buscar recepciones (stock.picking)
                        pickings = pol.order_id.picking_ids.filtered(lambda p: p.state != 'cancel')
                        if pickings:
                            # Ejemplo: tomar la primera recepción asociada
                            scheduled_dates = [d for d in pickings.mapped('scheduled_date') if d]
                            deadline_dates = [d for d in pickings.mapped('date_deadline') if d]
                            done_dates = [d for d in pickings.mapped('date_done') if d]

                            fecha_campo = line.request_id.date_planned#str(min(scheduled_dates)) if scheduled_dates else ""
                            fecha_dt = fields.Datetime.to_datetime(fecha_campo)
        
                            fecha_bodega = str(min(deadline_dates)) if deadline_dates else ""
                            fecha_arrivo = str(max(done_dates)) if done_dates else ""
            #sheet.write(row, 7, fecha_campo)   # Fecha en campo
            sheet.write_datetime(row, 7, fecha_dt, date_format)
            sheet.write(row, 8, order_name)
            
            sheet.write(row, 9, fecha_bodega)  # Fecha llegada bodega
            sheet.write(row, 10, fecha_arrivo) # Fecha arrivo real
            sheet.write(row, 11, purchase_state)

            sheet.write(row, 12, line.product_id.referencia_anterior or "")
            sheet.write(row, 13, line.product_brand_id.name or "")
            sheet.write(row, 14, line.qty_done or 0)
            sheet.write(row, 15, line.qty_available or 0)
            sheet.write(row, 16, line.request_id.requested_by.name or "")

            row += 1

        workbook.close()
        output.seek(0)

        file_content = base64.b64encode(output.read())
        output.close()

        wizard = self.env['purchase.request.line.export.wizard'].create({
            'file_data': file_content,
            'file_name': 'Requisiciones.xlsx'
        })
        return { 'type': 'ir.actions.act_window', 'res_model': 'purchase.request.line.export.wizard', 'view_mode': 'form', 'res_id': wizard.id, 'target': 'new', }
    # @api.constrains('analytic_distribution')
    # def _check_analytic_distribution(self):
    #     for record in self:
    #         if not record.analytic_distribution and record.product_id: 
    #             raise UserError(_("No puedes crear o modificar una requisicion de compra sin haber ingresado la distribucion analítica, para el producto '%s'.", record.product_id.default_code))
