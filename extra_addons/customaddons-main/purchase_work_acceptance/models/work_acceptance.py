# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WorkAcceptance(models.Model):
    _name = "work.acceptance"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin"]
    _description = "Work Acceptance"
    _order = "id desc"

    name = fields.Char(required=True, index=True, copy=False, default="New")
    date_due = fields.Datetime(
        string="Due Date",
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
    invoice_ref = fields.Char(string="Invoice Reference", copy=False)
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        required=True,
        change_default=True,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    responsible_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible Person",
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
    wa_line_ids = fields.One2many(
        comodel_name="work.acceptance.line",
        inverse_name="wa_id",
        string="Work Acceptance Lines",
    )
    notes = fields.Text()
    product_id = fields.Many2one(
        comodel_name="product.product",
        related="wa_line_ids.product_id",
        string="Product",
        readonly=False,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Work Acceptance Representative",
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
    purchase_id = fields.Many2one(
        comodel_name="purchase.order", string="Purchase Order", readonly=True
    )
    name_rs = fields.Char(required=True, index=True, copy=False, default="New")
    invoice_ids = fields.One2many(
        'account.move', 'wa_id', string='Facturas'
    )
    invoice_count = fields.Integer(compute='_compute_invoice_count')
    date_ini = fields.Date(
        string="Fecha Inicio Periodo",
        required=True
    )
    date_fin = fields.Date(
        string="Fecha Fin Periodo",
        required=True
    )
    invoice_status = fields.Selection(
        selection=[
            ('no_invoice', 'Sin Factura'),
            ('to_pay', 'Facturado sin Pagar'),
            ('paid', 'Pagado')
        ],
        string='Estado de Facturación',
        compute='_compute_invoice_status',
        store=True
    )

    @api.depends('invoice_ids.payment_state')
    def _compute_invoice_status(self):
        for wa in self:
            if not wa.invoice_ids:
                wa.invoice_status = 'no_invoice'
            elif all(inv.payment_state == 'paid' for inv in wa.invoice_ids):
                wa.invoice_status = 'paid'
            else:
                wa.invoice_status = 'to_pay'

    def _compute_invoice_count(self):
        for wa in self:
            wa.invoice_count = len(wa.invoice_ids)

    def action_create_invoice(self):
        self.ensure_one()
        purchase = self.purchase_id

        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': purchase.partner_id.id,
            'currency_id': purchase.currency_id.id,
            'invoice_origin': purchase.name,
            'invoice_date': fields.Date.context_today(self),
            'wa_id': self.id,
            'invoice_line_ids': [],
        }

        for line in self.wa_line_ids:
            invoice_vals['invoice_line_ids'].append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': line.product_qty,
                'price_unit': line.price_unit,
                'discount': line.discount or 0.0,
                'product_uom_id': line.product_uom.id,
                'analytic_distribution': line.purchase_line_id.analytic_distribution,
                'account_id': line.product_id.property_account_expense_id.id or line.product_id.categ_id.property_account_expense_categ_id.id,
            }))

        invoice = self.env['account.move'].create(invoice_vals)
        return {
            'name': _('Factura'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'target': 'current',
        }
    
    def action_view_invoices(self):
        self.ensure_one()
        action = self.env.ref('account.action_move_in_invoice_type').read()[0]
        action['domain'] = [('id', 'in', self.invoice_ids.ids)]
        action['context'] = {'default_wa_id': self.id}
        return action


    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         if vals.get("name", "New") == "New":
    #             vals["name"] = (
    #                 self.env["ir.sequence"].next_by_code("work.acceptance") or "/"
    #             )
    #     return super().create(vals_list)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            context = self.env.context
            purchase_id = context.get("default_purchase_id")

            if not purchase_id:
                raise UserError("No se puede crear una recepción sin una Orden de Compra.")

            # Obtener la última recepción de servicio (RS) para la misma OC
            existing_rs = self.search([("purchase_id", "=", purchase_id)], order="id desc", limit=1)

            if existing_rs and existing_rs.name_rs and existing_rs.name_rs.startswith("PLANILLA"):
                last_seq_num = int(existing_rs.name_rs.replace("PLANILLA", ""))  # Extraer el número de la última RS
                new_seq_num = last_seq_num + 1  # Incrementar el número
            else:
                new_seq_num = 1  # Si es la primera RS de esta OC

            vals["name_rs"] = f"PLANILLA{new_seq_num:04d}"  # Formato RS0001, RS0002, etc.

            # Generar secuencia normal de WA si aún no tiene un nombre
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("work.acceptance") or "/"

        return super().create(vals_list)

    def button_accept(self, force=False):
        if self.env.context.get("manual_date_accept"):
            wizard = self.env.ref(
                "purchase_work_acceptance.view_work_accepted_date_wizard"
            )
            return {
                "name": _("Select Accept Date"),
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "res_model": "work.accepted.date.wizard",
                "views": [(wizard.id, "form")],
                "view_id": wizard.id,
                "target": "new",
            }
        self._unlink_zero_quantity()
        date_accept = force or fields.Datetime.now()
        self.write({"state": "accept", "date_accept": date_accept})
        #Sincronizar qty_received con qty_accepted en las líneas de la OC
        for wa in self:
            for wa_line in wa.wa_line_ids:
                pol = wa_line.purchase_line_id
                if pol and pol.product_id.detailed_type == 'service':
                    pol.qty_received = pol.qty_accepted

    def button_draft(self):
        picking_obj = self.env["stock.picking"]
        wa_ids = picking_obj.search([("wa_id", "in", self.ids)])
        if wa_ids:
            raise UserError(
                _(
                    "Unable set to draft this work acceptance. "
                    "You must first cancel the related receipts."
                )
            )
        self.write({"state": "draft"})

    def button_cancel(self):
        self.write({"state": "cancel"})

    def _unlink_zero_quantity(self):
        wa_line_zero_quantity = self.wa_line_ids.filtered(
            lambda l: l.product_qty == 0.0
        )
        wa_line_zero_quantity.unlink()

    def _get_valid_wa(self, doctype, order_id):
        """Get unused WA when validate invoice or picking"""
        order = self.env["purchase.order"].browse(order_id)
        all_wa = self.env["work.acceptance"].search(
            [
                ("state", "=", "accept"),
                ("purchase_id", "=", order.id),
            ]
        )
        if doctype == "invoice":
            used_wa = order.invoice_ids.filtered(
                lambda l: l.state in ("draft", "posted")
            ).mapped("wa_id")
            return all_wa - used_wa
        if doctype == "picking":
            used_wa = order.picking_ids.mapped("wa_id")
            return all_wa - used_wa
        return all_wa
    
    def envio_wa_aprobado(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        wa = self.env['work.acceptance'].search([
                ('state', '=', 'accept')
            ])
        table_rows = ""
        for x in wa:
            # Filtrar órdenes asignadas a ese aprobador
            if wa.invoice_ids:
                continue
            fecha_aceptacion = x.date_accept.strftime('%Y-%m-%d')
            
            url = f"{base_url}/web#id={x.id}&model=work.acceptance&view_type=form"
            
            table_rows += f"""
                <tr>
                    <td>{x.name}</td>
                    <td>{x.name_rs}</td>
                    <td>{x.partner_id.name}</td>
                    <td>{x.responsible_id.name}</td>
                    <td>{x.company_id.name}</td>
                    <td>{x.purchase_id.name}</td>
                    <td>{fecha_aceptacion}</td>
                    <td><a href="{url}">Crear Factura</a></td>
                </tr>
            """

        body_html = f"""
            <p>Estimados,</p>
            <p>Tiene las siguientes órdenes de aceptacion de trabajo por servicios para crear facturas:</p>
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; font-family: Arial;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th>Orden</th>
                        <th>Planilla</th>
                        <th>Proveedor</th>
                        <th>Solicitante</th>
                        <th>Compania</th>
                        <th>Orden de Compra</th>
                        <th>Fecha de Aceptacion</th>
                        <th>Acción</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
            <p>Por favor ingrese a Odoo para revisar y generar la factura.</p>
        """

        # Enviar el correo
        self.env['mail.mail'].create({
            'subject': 'Órdenes de aceptacion de servicio pendientes de facturar',
            'body_html': body_html,
            'email_to': 'lsalazar@gpsgroup.com.ec, ymorales@gpsgroup.com.ec',
            'auto_delete': True,
        }).send()

    def envio_wa_facturadas(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        wa_facturadas = self.env['work.acceptance'].search([
            ('state', '=', 'accept'),
            ('invoice_ids', '!=', False)
        ])
        
        table_rows = ""
        for x in wa_facturadas:
            if not x.invoice_ids:
                continue

            # Determinar estado de pago
            if all(inv.payment_state == 'paid' for inv in x.invoice_ids):
                estado_pago = 'Pagado'
            elif any(inv.payment_state == 'partial' for inv in x.invoice_ids):
                estado_pago = 'Parcialmente Pagado'
            else:
                estado_pago = 'No Pagado'

            fecha_aceptacion = x.date_accept.strftime('%Y-%m-%d') if x.date_accept else ''
            url = f"{base_url}/web#id={x.id}&model=work.acceptance&view_type=form"

            table_rows += f"""
                <tr>
                    <td>{x.name}</td>
                    <td>{x.name_rs}</td>
                    <td>{x.partner_id.name}</td>
                    <td>{x.responsible_id.name}</td>
                    <td>{x.company_id.name}</td>
                    <td>{x.purchase_id.name}</td>
                    <td>{fecha_aceptacion}</td>
                    <td>{estado_pago}</td>
                    <td><a href="{url}">Ver Orden</a></td>
                </tr>
            """

        if not table_rows:
            return

        body_html = f"""
            <p>Estimados,</p>
            <p>Estas son las órdenes de aceptación de trabajo que ya han sido facturadas:</p>
            <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; font-family: Arial;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th>Orden</th>
                        <th>Planilla</th>
                        <th>Proveedor</th>
                        <th>Solicitante</th>
                        <th>Compañía</th>
                        <th>Orden de Compra</th>
                        <th>Fecha de Aceptación</th>
                        <th>Estado de Pago</th>
                        <th>Acción</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
            <p>Por favor ingrese a Odoo para revisar el estado de pagos.</p>
        """

        self.env['mail.mail'].create({
            'subject': 'Órdenes de aceptación facturadas – Estado de pago',
            'body_html': body_html,
            'email_to': 'mmorquecho@gpsgroup.com.ec, aimbaquingo@gpsgroup.com.ec',
            'auto_delete': True,
        }).send()


class WorkAcceptanceLine(models.Model):
    _name = "work.acceptance.line"
    _description = "Work Acceptance Line"
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
    wa_id = fields.Many2one(
        comodel_name="work.acceptance",
        string="WA Reference",
        index=True,
        required=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="wa_id.partner_id",
        string="Partner",
        readonly=True,
    )
    responsible_id = fields.Many2one(
        comodel_name="res.users",
        related="wa_id.responsible_id",
        string="Responsible Person",
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="wa_id.currency_id", string="Currency", readonly=True
    )
    date_due = fields.Datetime(
        related="wa_id.date_due", string="Due Date", readonly=True
    )
    date_receive = fields.Datetime(
        related="wa_id.date_receive", string="Received Date", readonly=True
    )
    date_accept = fields.Datetime(
        related="wa_id.date_accept", string="Accepted Date", readonly=True
    )
    purchase_line_id = fields.Many2one(
        comodel_name="purchase.order.line",
        string="Purchase Order Line",
        ondelete="set null",
        index=True,
        readonly=False,
    )
    purchase_id = fields.Many2one(
        related='purchase_line_id.order_id',
        store=True,
        string='Orden de Compra'
    )
    product_id = fields.Many2one(
        related='purchase_line_id.product_id',
        store=True,
        string='Producto'
    )
    date_accept = fields.Datetime(
        related='wa_id.date_accept',
        store=True,
        string='Fecha de Aceptación'
    )
    discount = fields.Float("Descuento (%)")

    @api.depends('product_qty', 'price_unit', 'discount')
    def _compute_amount(self):
        for line in self:
            price_after_discount = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            line.price_subtotal = line.product_qty * price_after_discount
