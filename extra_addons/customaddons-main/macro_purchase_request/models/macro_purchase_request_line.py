# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.populate import compute

_STATES = [
    ("draft", "Draft"),
    ("to_approve", "To be approved"),
    ("approved", "Approved"),
    ("in_progress", "In progress"),
    ("done", "Done"),
    ("rejected", "Rejected"),
]


class MacroPurchaseRequestLine(models.Model):

    _name = "macro.purchase.request.line"
    _description = "Macro Purchase Request Line"
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin"]
    _order = "id desc"

    name = fields.Char(string="Description", tracking=True)
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="UoM",
        tracking=True,
        domain="[('category_id', '=', product_uom_category_id)]",
    )
    product_uom_category_id = fields.Many2one(
            related="product_uom_id.category_id",
            string="UoM Category",
            store=True,
            readonly=True
        )
    product_qty = fields.Float(
        string="Quantity", tracking=True, digits="Product Unit of Measure"
    )

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
        comodel_name="macro.purchase.request",
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
    is_editable_assigned_to = fields.Boolean(readonly=True)
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
    sale_order_line_id = fields.Many2one('sale.order.line', string='Línea de Pedido', index=True, help="Referencia a la línea del pedido de venta que originó esta línea de requisición",)
    
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        domain=[("purchase_ok", "=", True)],
        tracking=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)
    analytic_account_names = fields.Char(
        string='Cuentas Analíticas',
        compute='_compute_analytic_account_names',
        store = True
    )
    tipo_costo = fields.Char('Tipo Costo')
    rubro = fields.Char('Rubro')
    request_type = fields.Selection(
        related="request_id.request_type",
        string="Tipo Requisicion",
        store=True,
    )
    costo_unit_apu = fields.Float("C.Uni Apu",    digits=(16,4))

    @api.depends(
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
        res = super(MacroPurchaseRequestLine, self).write(vals)
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

        return super(MacroPurchaseRequestLine, self).create(vals_list)
    

    def _get_next_sequence(self, request_id):
        """ Busca la siguiente secuencia disponible para la requisición """
        last_line = self.search([('request_id', '=', request_id)], order="sequence desc", limit=1)
        return last_line.sequence + 1 if last_line else 10

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
        return super(MacroPurchaseRequestLine, self).unlink()
    
    @api.constrains('analytic_distribution')
    def _check_analytic_distribution(self):
        for record in self:
            if not record.analytic_distribution and record.product_id: 
                raise UserError(_("No puedes crear o modificar una requisicion de compra sin haber ingresado la distribucion analítica, para el producto '%s'.", record.product_id.default_code))
