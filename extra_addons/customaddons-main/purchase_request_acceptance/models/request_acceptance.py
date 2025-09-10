# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class RequestAcceptance(models.Model):
    _name = "request.acceptance"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin","analytic.mixin"]
    _description = "Request Acceptance"
    _order = "id desc"

    @api.model
    def _default_picking_type(self):
        type_obj = self.env["stock.picking.type"]
        company_id = self.env.context.get("company_id") or self.env.company.id
        types = type_obj.search(
            [("code", "=", "incoming"), ("warehouse_id.company_id", "=", company_id)]
        )
        if not types:
            types = type_obj.search(
                [("code", "=", "incoming"), ("warehouse_id", "=", False)]
            )
        return types[:1]
    
    name = fields.Char(required=True, index=True, copy=False, default="New")
    date_due = fields.Datetime(
        string="Fecha Llegada",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    date_receive = fields.Datetime(
        string="Received Date",
        default=fields.Datetime.now,
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    date_accept = fields.Datetime(string="Accepted Date", readonly=True)
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        required=False,
        change_default=True,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    responsible_id = fields.Many2one(
        comodel_name="res.users",
        string="Solicitante",
        default=lambda self: self.env.user,
        required=True,
        change_default=True,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
        readonly=True,
    )
    state = fields.Selection(
        [("draft", "Draft"), ("accept", "Accepted"), ("cancel", "Cancelled")],
        string="Status",
        readonly=True,
        index=True,
        copy=False,
        default="draft",
        tracking=True,
    )
    pr_line_ids = fields.One2many(
        comodel_name="request.acceptance.line",
        inverse_name="pr_id",
        string="Request Acceptance Lines",
    )
    notes = fields.Text()
    product_id = fields.Many2one(
        comodel_name="product.product",
        related="pr_line_ids.product_id",
        string="Product",
        readonly=False,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Request Acceptance Representative",
        default=lambda self: self.env.user,
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    request_id = fields.Many2one(
        comodel_name="macro.purchase.request", string="Purchase Request", readonly=True
    )
    name_rs = fields.Char(required=True, index=True, copy=False, default="New")
    request_type = fields.Selection(
        [("service", "Servicio"), ("product", "Producto"), ("mixed", "Producto y Servicio")],
        string="Tipo de Requisicion",
        default="product",
        compute="_compute_request_type",
        store=True,
    )
    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Picking Type",
        required=True,
        default=_default_picking_type,
    )
    purchase_request_ids = fields.One2many(
        'purchase.request', 'request_acceptance_id', string='Requisiciones'
    )
    requisicion_count = fields.Integer(compute='_compute_requisicion_count')

    def action_view_requisiciones(self):
        self.ensure_one()
        action = self.env.ref('purchase_request.purchase_request_form_action').read()[0]
        action['domain'] = [('id', 'in', self.purchase_request_ids.ids)]
        action['context'] = {'default_request_acceptance_id': self.id}
        return action

    def _compute_requisicion_count(self):
        for pr in self:
            pr.requisicion_count = len(pr.purchase_request_ids)

    @api.depends("pr_line_ids.product_id.detailed_type")
    def _compute_request_type(self):
        for rec in self:
            if all([line.product_id.detailed_type in ("service", "consu") for line in rec.pr_line_ids]):
                rec.request_type = "service"
            elif all([line.product_id.detailed_type == "product" for line in rec.pr_line_ids]):
                rec.request_type = "product"
            else:
                rec.request_type = "mixed"
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            context = self.env.context
            request_id = context.get("default_request_id")

            # if not request_id:
            #     raise UserError("No se puede crear una Requisicion sin un Macro Requisicion.")

            # Obtener la última recepción de servicio (RS) para la misma OC
            existing_rs = self.search([("request_id", "=", request_id)], order="id desc", limit=1)

            if existing_rs and existing_rs.name_rs and existing_rs.name_rs.startswith("Requisicion"):
                last_seq_num = int(existing_rs.name_rs.replace("Requisicion", ""))  # Extraer el número de la última RS
                new_seq_num = last_seq_num + 1  # Incrementar el número
            else:
                new_seq_num = 1  # Si es la primera RS de esta MRQ

            vals["name_rs"] = f"Requisicion{new_seq_num:04d}"  # Formato RS0001, RS0002, etc.

            # Generar secuencia normal de WA si aún no tiene un nombre
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("request.acceptance") or "/"

        return super().create(vals_list)

    def button_accept(self, force=False):
        if self.env.context.get("manual_date_accept"):
            wizard = self.env.ref(
                "purchase_request_acceptance.view_request_accepted_date_wizard"
            )
            return {
                "name": _("Generacion de Requisicion"),
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "res_model": "request.accepted.date.wizard",
                "views": [(wizard.id, "form")],
                "view_id": wizard.id,
                "target": "new",
            }

        # Validación de cantidades aceptadas y productos opcionales
        for pr in self:
            for line in pr.pr_line_ids:
                if not line.purchase_line_id:
                    continue  # línea sin vínculo, ignorar

                macro_line = line.purchase_line_id
                original_product = macro_line.product_id
                accepted_product = line.product_id

                # Validar si el producto aceptado es el mismo o un opcional
                original_template = original_product.product_tmpl_id
                accepted_template = accepted_product.product_tmpl_id

                if accepted_template != original_template and accepted_template not in original_template.optional_product_ids:
                    raise UserError(_(
                        "El producto aceptado '%s' no coincide con el original '%s' ni es uno de sus productos opcionales."
                    ) % (
                        accepted_product.display_name,
                        original_product.display_name,
                    ))

                # Validar la cantidad total aceptada para esa macro línea
                total_accepted = sum(
                    other_line.product_qty
                    for other in self.search([("state", "=", "accept"), ("request_id", "=", pr.request_id.id)])
                    for other_line in other.pr_line_ids
                    if other_line.purchase_line_id == macro_line
                )
                total_accepted += line.product_qty

                if total_accepted > macro_line.product_qty:
                    raise UserError(_(
                        "No puedes aceptar más de la cantidad solicitada en la macro requisición.\n"
                        "Producto base: %s\n"
                        "Solicitado: %s - Intentado aceptar: %s"
                    ) % (
                        original_product.display_name,
                        macro_line.product_qty,
                        total_accepted
                    ))

        self._unlink_zero_quantity()
        date_accept = force or fields.Datetime.now()

        # Crear la requisición (una sola por documento de aceptación)
        for pr in self:
            purchase_req = self.env['purchase.request'].create({
                'origin': pr.name_rs,
                'requested_by': pr.responsible_id.id,
                'company_id': pr.company_id.id,
                'picking_type_id': pr.picking_type_id.id,
                'date_start': fields.Date.today(),
                'request_acceptance_id': pr.id,
                'permite_aprobar': True,
                'analytic_distribution': pr.analytic_distribution,
            })

            for line in pr.pr_line_ids.filtered(lambda l: l.product_qty > 0 and l.purchase_line_id):
                self.env['purchase.request.line'].create({
                    'request_id': purchase_req.id,
                    'product_id': line.product_id.id,
                    'name': line.name or line.product_id.display_name,
                    'product_qty': line.product_qty,
                    'product_uom_id': line.product_uom.id,
                    'date_required': pr.date_due,
                    'analytic_distribution': line.analytic_distribution,
                    'rubro': line.rubro,
                    'tipo_costo': line.tipo_costo,
                    'costo_uni_apu':line.costo_uni_apu,
                    'product_brand_id': line.product_id.product_brand_id.id,
                    'product_categ_id': line.product_id.categ_id.id,
                    'request_acceptance_line_id': line.purchase_line_id.id if line.purchase_line_id else False,
                })

        self.write({"state": "accept", "date_accept": date_accept})

    def button_draft(self):
        self.write({"state": "draft"})

    def button_cancel(self):
        self.write({"state": "cancel"})

    def _unlink_zero_quantity(self):
        pr_line_zero_quantity = self.pr_line_ids.filtered(
            lambda l: l.product_qty == 0.0
        )
        pr_line_zero_quantity.unlink()

    def _get_valid_wa(self, doctype, order_id):
        """Get unused WA when validate invoice or picking"""
        order = self.env["macro.purchase.order"].browse(order_id)
        all_pr = self.env["request.acceptance"].search(
            [
                ("state", "=", "accept"),
                ("request_id", "=", order.id),
            ]
        )
        return all_pr
    

class RequestAcceptanceLine(models.Model):
    _name = "request.acceptance.line"
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _description = "Request Acceptance Line"
    _order = "id"

    name = fields.Text(string="Description", required=True)
    product_qty = fields.Float(
        string="Quantity", required=True, digits="Product Unit of Measure"
    )
    product_id = fields.Many2one(
        comodel_name="product.product", string="Product", required=True
    )
    product_uom = fields.Many2one(
        comodel_name="uom.uom", string="Product Unit of Measure", required=True
    )
    price_unit = fields.Float(string="Unit Price", required=True)
    price_subtotal = fields.Monetary(compute="_compute_amount", string="Subtotal")
    pr_id = fields.Many2one(
        comodel_name="request.acceptance",
        string="PR Reference",
        index=True,
        required=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="pr_id.partner_id",
        string="Partner",
        readonly=True,
    )
    responsible_id = fields.Many2one(
        comodel_name="res.users",
        related="pr_id.responsible_id",
        string="Responsible Person",
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="pr_id.currency_id", string="Currency", readonly=True
    )
    date_due = fields.Datetime(
        related="pr_id.date_due", string="Due Date", readonly=True
    )
    date_receive = fields.Datetime(
        related="pr_id.date_receive", string="Received Date", readonly=True
    )
    date_accept = fields.Datetime(
        related="pr_id.date_accept", string="Accepted Date", readonly=True
    )
    purchase_line_id = fields.Many2one(
        comodel_name="macro.purchase.request.line",
        string="Macro Purchase Request Line",
        ondelete="set null",
        index=True,
        readonly=False,
    )
    request_id = fields.Many2one(
        related='purchase_line_id.request_id',
        store=True,
        string='Macro Requisicion de Compra'
    )
    product_id = fields.Many2one(
        related='purchase_line_id.product_id',
        store=True,
        string='Producto'
    )
    date_accept = fields.Datetime(
        related='pr_id.date_accept',
        store=True,
        string='Fecha de Aceptación'
    )
    discount = fields.Float("Descuento (%)")
    analytic_account_names = fields.Char(
        string='Cuentas Analíticas',
        compute='_compute_analytic_account_names',
        store = True
    )
    tipo_costo = fields.Char('Tipo Costo')
    rubro = fields.Char('Rubro')
    costo_uni_apu = fields.Float("C.Uni Apu",    digits=(16,4))

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

    @api.depends('product_qty', 'price_unit', 'discount')
    def _compute_amount(self):
        for line in self:
            price_after_discount = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            line.price_subtotal = line.product_qty * price_after_discount
