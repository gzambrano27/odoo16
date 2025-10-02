# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from datetime import datetime, timedelta, date
import base64
import xlsxwriter
import io
import json

_STATES = [
    ("draft", "Draft"),
    ("to_approve", "To be approved"),
    ("approved", "Approved"),
    ("in_progress", "In progress"),
    ("done", "Done"),
    ("rejected", "Rejected"),
]
_STATESREV = [
    ("revisado", "Revisado Supply"),
    ("no revisado", "No Revisado Supply")
]

class PurchaseRequest(models.Model):

    _name = "purchase.request"
    _description = "Purchase Request"
    _inherit = ["mail.thread", "mail.activity.mixin","analytic.mixin"]
    _order = 'priority desc, id desc'

    @api.model
    def _company_get(self):
        return self.env["res.company"].browse(self.env.company.id)

    @api.model
    def _get_default_requested_by(self):
        return self.env["res.users"].browse(self.env.uid)

    @api.model
    def _get_default_name(self):
        return self.env["ir.sequence"].next_by_code("purchase.request.seq")

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

    @api.depends("state")
    def _compute_is_editable(self):
        for rec in self:
            if rec.state in (
                "to_approve",
                "approved",
                "rejected",
                "in_progress",
                "done",
            ):
                rec.is_editable = False
            else:
                rec.is_editable = True

    name = fields.Char(
        string="Request Reference",
        required=True,
        default=lambda self: _("New"),
        tracking=True,
    )
    is_name_editable = fields.Boolean(
        default= False #lambda self: self.env.user.has_group("base.group_no_one"),
    )
    origin = fields.Char(string="Source Document")
    date_start = fields.Date(
        string="Creation date",
        help="Date when the user initiated the request.",
        default=fields.Date.context_today,
        tracking=True,
    )
    requested_by = fields.Many2one(
        comodel_name="res.users",
        required=True,
        copy=False,
        tracking=True,
        default=_get_default_requested_by,
        index=True,
    )
    assigned_to = fields.Many2one(
        comodel_name="res.users",
        string="Approver",
        tracking=True,
        # domain=lambda self: [
        #     (
        #         "groups_id",
        #         "in",
        #         self.env.ref("purchase_request.group_purchase_request_manager").id,
        #     )
        # ],
        index=True,
    )
    description = fields.Text()
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=False,
        default=_company_get,
        tracking=True,
    )
    line_ids = fields.One2many(
        comodel_name="purchase.request.line",
        inverse_name="request_id",
        string="Products to Purchase",
        readonly=True,
        copy=True,
        tracking=True,
        states={"draft": [("readonly", False)]},
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        related="line_ids.product_id",
        string="Product",
        readonly=True,
    )
    state = fields.Selection(
        selection=_STATES,
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        default="draft",
    )
    is_editable = fields.Boolean(compute="_compute_is_editable", readonly=True)
    to_approve_allowed = fields.Boolean(compute="_compute_to_approve_allowed")
    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Picking Type",
        required=True,
        default=_default_picking_type,
    )
    group_id = fields.Many2one(
        comodel_name="procurement.group",
        string="Procurement Group",
        copy=False,
        index=True,
    )
    line_count = fields.Integer(
        string="Purchase Request Line count",
        compute="_compute_line_count",
        readonly=True,
    )
    move_count = fields.Integer(
        string="Stock Move count", compute="_compute_move_count", readonly=True
    )
    purchase_count = fields.Integer(
        string="Purchases count", compute="_compute_purchase_count", readonly=True
    )
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    estimated_cost = fields.Monetary(
        compute="_compute_estimated_cost",
        string="Total Estimated Cost",
        store=True,
    )
    date_planned = fields.Date(
        string="Fecha Llegada",
        default=lambda self: fields.Date.to_string(datetime.today() + timedelta(days=15)),#fields.Date.context_today,
        tracking=True,
    )
    estado_revision = fields.Selection(
        selection=_STATESREV,
        string="Estado Revision Supply",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        default="no revisado",
    )
    show_estado_revision = fields.Boolean(compute='_compute_show_estado_revision')
    mrp_production_id = fields.Many2one("mrp.production", string="Manufacturing Order")
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'Urgent')], 'Priority', default='0', index=True)
    
    request_type = fields.Selection(
        [("service", "Servicio"), ("product", "Producto"), ("mixed", "Producto y Servicio")],
        string="Tipo de Requisicion",
        default="product",
        compute="_compute_request_type",
        store=True,
    )
    file_data = fields.Binary(string="Archivo Excel", readonly=True)
    analytic_distribution = fields.Json(
        string="Analitica",
        default={},
        help="Distribucion analitica que se aplicara a todas las lineas",
    )
    rendimiento = fields.Integer('Cant. por Dia', help='Debe Ingresar la cantidad por dia')
    equipos = fields.Integer('Cant. Equipos', help='Debe Ingresar la cantidad de equipos')
    personal_min_equipo = fields.Integer('Personal Min. por Equipo', help='Debe Ingresar el personal minimo por equipo')
    duracion_estimada = fields.Integer('Duracion Estimada', help='Duracion estimada de Obra')
    tipo_pedido = fields.Selection(
        [("administrativo", "Administrativo"), ("presidencia", "Presidencia"), ("proyecto", "Proyecto")],
        string="Tipo de Pedido",
        default="proyecto",
        compute="_compute_tipo_pedido",
        store=True,
    )
    fiscalizador_id = fields.Many2one(
        comodel_name="res.users",
        copy=False,
        tracking=True,
        index=True,
        domain=lambda self: [
            ("groups_id", "in", self.env.ref("purchase_request.group_purchase_request__ficalizador").id)
        ],
        #default=lambda self: self._default_fiscalizador(),
    )
    tipo_contrato = fields.Selection(
        [("por ejecutar", "Por Ejecutar"), ("en ejecucion", "En Ejecucion"), ("ejecutado", "Ejecutado")],
        string="Tipo de Contrato",
        copy=False,
        tracking=True,
    )

    @api.model
    def _default_fiscalizador(self):
        """Asigna el usuario actual si pertenece al grupo de fiscalizadores"""
        user = self.env.user
        if user.has_group("purchase_request.group_purchase_request__ficalizador"):
            return user.id
        return False
    
    # @api.constrains("fiscalizador_id", "request_type")
    # def _check_fiscalizador_required(self):
    #     for rec in self:
    #         # Si la requisición es de tipo servicio o mixto
    #         if rec.request_type in ("service", "mixed") and not rec.fiscalizador_id:
    #             raise UserError(_("Debe seleccionar un Fiscalizador para requisiciones de tipo Servicio o Producto y Servicio."))
            
    # @api.constrains("tipo_contrato", "request_type")
    # def _check_tipo_contrato_required(self):
    #     for rec in self:
    #         # Si la requisición es de tipo servicio o mixto
    #         if rec.request_type in ("service", "mixed") and not rec.tipo_contrato:
    #             raise UserError(_("Debe seleccionar un Tipo de Contrato para requisiciones de tipo Servicio o Producto y Servicio."))

    @api.constrains("fiscalizador_id", "tipo_contrato", "request_type", "tipo_pedido", "date_start", "state")
    def _check_fiscalizador_tipo_contrato_proyecto(self):
        for rec in self:
            # Aplica solo a requisiciones de tipo "proyecto"
            if rec.tipo_pedido != "proyecto":
                continue

            # Condición: nuevas (>= hoy) o en borrador
            if (rec.date_start and rec.date_start >= date.today()) or rec.state == "draft":
                # Requisiciones de tipo servicio o mixto
                if rec.request_type in ("service", "mixed"):
                    if not rec.fiscalizador_id:
                        raise UserError(_("Debe seleccionar un Fiscalizador para requisiciones de tipo Proyecto (Servicio o Producto y Servicio)."))
                    if not rec.tipo_contrato:
                        raise UserError(_("Debe seleccionar un Tipo de Contrato para requisiciones de tipo Proyecto (Servicio o Producto y Servicio)."))
                    
    @api.onchange("analytic_distribution")
    def _onchange_analytic_distribution(self):
        for rec in self:
            if rec.analytic_distribution:
                for line in rec.line_ids:
                    line.analytic_distribution = rec.analytic_distribution

    @api.constrains('analytic_distribution')
    def _check_analytic_distribution_required(self):
        for rec in self:
            if not rec.analytic_distribution and rec.state=='draft':#and (rec.date_start >= date(2025, 8, 7) or rec.state=='draft'):
                raise UserError(_('Debe llenar la distribución analítica en la cabecera de la requisición.'))

    @api.depends("requested_by")
    def _compute_tipo_pedido(self):
        """ Asigna tipo_pedido según grupo del solicitante """
        for rec in self:
            tipo = "proyecto"  # valor por defecto

            if rec.requested_by:
                user = rec.requested_by

                # grupos: ajusta los XML-ID reales de tus grupos
                group_admin = self.env.ref("account_payment_purchase.group_purchase_admin", raise_if_not_found=False)
                group_presidencia = self.env.ref("account_payment_purchase.group_purchase_presidencia", raise_if_not_found=False)

                if group_admin and group_admin in user.groups_id:
                    tipo = "administrativo"
                elif group_presidencia and group_presidencia in user.groups_id:
                    tipo = "presidencia"

            rec.tipo_pedido = tipo

    @api.depends("line_ids.product_id.detailed_type")
    def _compute_request_type(self):
        for rec in self:
            if all([line.product_id.detailed_type in ("service", "consu") for line in rec.line_ids]):
                rec.request_type = "service"
            elif all([line.product_id.detailed_type == "product" for line in rec.line_ids]):
                rec.request_type = "product"
            else:
                rec.request_type = "mixed"

    @api.depends('state')
    def _compute_show_estado_revision(self):
        for rec in self:
            rec.show_estado_revision = rec.state == 'approved'
        # for rec in self:
        #     rec.show_estado_revision = False
        #     print(self.env.user.has_group)
        #     if rec.state == 'approved' and self.env.user.has_group('purchase_request.group_purchase_request_supply') and not self.env.user.has_group('purchase_request.group_purchase_request_manager'):
        #         rec.show_estado_revision = True

    # @api.constrains('line_ids')
    # def _check_line_items(self):
    #     for request in self:
    #         if not request.line_ids:
    #             raise UserError(_("No puedes crear una solicitud sin al menos una línea de producto."))

    @api.depends("line_ids", "line_ids.estimated_cost")
    def _compute_estimated_cost(self):
        for rec in self:
            rec.estimated_cost = sum(rec.line_ids.mapped("estimated_cost"))

    @api.depends("line_ids")
    def _compute_purchase_count(self):
        for rec in self:
            rec.purchase_count = len(rec.mapped("line_ids.purchase_lines.order_id"))

    def action_view_purchase_order(self):
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.purchase_rfq")
        lines = self.mapped("line_ids.purchase_lines.order_id")
        if len(lines) > 1:
            action["domain"] = [("id", "in", lines.ids)]
        elif lines:
            action["views"] = [
                (self.env.ref("purchase.purchase_order_form").id, "form")
            ]
            action["res_id"] = lines.id
        return action

    @api.depends("line_ids")
    def _compute_move_count(self):
        for rec in self:
            rec.move_count = len(
                rec.mapped("line_ids.purchase_request_allocation_ids.stock_move_id")
            )

    def action_view_stock_picking(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock.action_picking_tree_all"
        )
        # remove default filters
        action["context"] = {}
        lines = self.mapped(
            "line_ids.purchase_request_allocation_ids.stock_move_id.picking_id"
        )
        if len(lines) > 1:
            action["domain"] = [("id", "in", lines.ids)]
        elif lines:
            action["views"] = [(self.env.ref("stock.view_picking_form").id, "form")]
            action["res_id"] = lines.id
        return action

    @api.depends("line_ids")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.mapped("line_ids"))

    def action_view_purchase_request_line(self):
        action = (
            self.env.ref("purchase_request.purchase_request_line_form_action")
            .sudo()
            .read()[0]
        )
        lines = self.mapped("line_ids")
        if len(lines) > 1:
            action["domain"] = [("id", "in", lines.ids)]
        elif lines:
            action["views"] = [
                (self.env.ref("purchase_request.purchase_request_line_form").id, "form")
            ]
            action["res_id"] = lines.ids[0]
        return action

    @api.depends("state", "line_ids.product_qty", "line_ids.cancelled")
    def _compute_to_approve_allowed(self):
        #for rec in self:
        #    rec.to_approve_allowed = rec.state == "draft" and any(
        #        not line.cancelled and line.product_qty for line in rec.line_ids
        #    )
        for rec in self:
            if rec.state == "draft":
                for line in rec.line_ids:
                    if not line.cancelled and line.product_qty >= 0:
                        if line.product_qty <= 0 and line.product_id:
                            raise UserError(_("Coloque la cantidad al producto '%s'.", line.product_id.default_code))
                        if line.product_id.categ_id.asset_fixed_control or line.product_id.categ_id.asset_fixed_depreciable:
                            if line.un_solo_custodio and (len(line.employees_ids.ids) != 1):
                                rec.to_approve_allowed = False
                                raise UserError(_("El producto '%s' es un activo fijo e indica que debe tener asignado un solo empleado, asegurese de hacerlo", line.product_id.default_code))
                            elif not line.un_solo_custodio and not (len(line.employees_ids.ids) == int(line.product_qty)):
                                rec.to_approve_allowed = False
                                raise UserError(_("El producto '%s' es un activo fijo y debe ser asignado a la misma cantidad de empleados.", line.product_id.default_code))
                            rec.to_approve_allowed = True
                        else:
                            if (len(line.employees_ids.ids) > 0):
                                raise UserError(_("El producto '%s'. No es un activo fijo por lo tanto no debe de ser asignado a empleados.", line.product_id.default_code))
                rec.to_approve_allowed = True
            else:
                rec.to_approve_allowed = False

    def copy(self, default=None):
        default = dict(default or {})
        self.ensure_one()
        default.update({"state": "draft", "name": self._get_default_name()})
        return super(PurchaseRequest, self).copy(default)

    @api.model
    def _get_partner_id(self, request):
        user_id = request.assigned_to or self.env.user
        return user_id.partner_id.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self._get_default_name()
        requests = super(PurchaseRequest, self).create(vals_list)

        for line in requests.line_ids:
            if not line.cancelled and line.product_qty >= 0:
                if line.product_qty <= 0 and line.product_id:
                    raise UserError(_("Coloque la cantidad al producto '%s'.", line.product_id.default_code))
                if line.product_id.categ_id.asset_fixed_control or line.product_id.categ_id.asset_fixed_depreciable:
                    if line.un_solo_custodio and (len(line.employees_ids.ids) != 1):
                        raise UserError(_("El producto '%s' es un activo fijo e indica que debe tener asignado un solo empleado, asegurese de hacerlo", line.product_id.default_code))
                    elif not line.un_solo_custodio and not (len(line.employees_ids.ids) == int(line.product_qty)):
                        raise UserError(_("El producto '%s' es un activo fijo y debe ser asignado a la misma cantidad de empleados.", line.product_id.default_code))
                else:
                    if (len(line.employees_ids.ids) > 0):
                        raise UserError(_("El producto '%s'. No es un activo fijo por lo tanto no debe de ser asignado a empleados.", line.product_id.default_code))

        for vals, request in zip(vals_list, requests):
            if vals.get("assigned_to"):
                partner_id = self._get_partner_id(request)
                request.message_subscribe(partner_ids=[partner_id])
        return requests

    def write(self, vals):
        if 'estado_revision' in vals:
            user_group_ids = self.env.user.groups_id.ids
            group_supply = self.env.ref('purchase_request.group_purchase_request_supply')
            group_manager = self.env.ref('purchase_request.group_purchase_request_manager')
            
            # Solo si está en supply y NO está en manager (sin herencia)
            if group_supply.id in user_group_ids and group_manager.id not in user_group_ids:
                pass  # permitido
            else:
                raise UserError("Solo los usuarios del grupo Supply, pueden modificar este campo.")
        res = super(PurchaseRequest, self).write(vals)
        for request in self:
            if vals.get("assigned_to"):
                partner_id = self._get_partner_id(request)
                request.message_subscribe(partner_ids=[partner_id])
        return res

    def _can_be_deleted(self):
        self.ensure_one()
        return self.state == "draft"

    def unlink(self):
        for request in self:
            if not request._can_be_deleted():
                raise UserError(
                    _("You cannot delete a purchase request which is not draft.")
                )
        return super(PurchaseRequest, self).unlink()

    def button_draft(self):
        self.mapped("line_ids").do_uncancel()
        return self.write({"state": "draft"})

    def button_to_approve(self):
        for rec in self:
            if not rec.analytic_distribution:
                raise UserError(_('Debe llenar la distribución analítica en la cabecera de la requisición antes de solicitar aprobación.'))
        self.to_approve_allowed_check()
        return self.write({"state": "to_approve"})

    def button_approved(self):
        group_gerencia = self.env.ref("account_payment_purchase.group_purchase_user_administrativo", raise_if_not_found=False)
        for rec in self:
            if rec.tipo_pedido in ("administrativo", "presidencia"):
                if not (group_gerencia and group_gerencia in self.env.user.groups_id):
                    raise UserError(_("Solo los usuarios del grupo Gerencia de Requisiciones departamentales pueden aprobar requisiciones de tipo Administrativo o Presidencia."))
        return self.write({"state": "approved"})

    def button_rejected(self):
        self.mapped("line_ids").do_cancel()
        return self.write({"state": "rejected"})

    def button_in_progress(self):
        return self.write({"state": "in_progress"})

    def button_done(self):
        return self.write({"state": "done"})

    def check_auto_reject(self):
        """When all lines are cancelled the purchase request should be
        auto-rejected."""
        for pr in self:
            if not pr.line_ids.filtered(lambda l: l.cancelled is False):
                pr.write({"state": "rejected"})

    def to_approve_allowed_check(self):
        for rec in self:
            if not rec.to_approve_allowed:
                raise UserError(
                    _(
                        "You can't request an approval for a purchase request "
                        "which is empty. (%s)"
                    )
                    % rec.name
                )
            
    def button_descargar(self):
        for record in self:
            # Crear el archivo Excel en memoria
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output)
            sheet = workbook.add_worksheet('PurchaseRequest')

            # Formatos
            title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
            header_format = workbook.add_format({'bold': True, 'align': 'left'})
            value_format = workbook.add_format({'align': 'left'})

            # Cabecera principal
            sheet.write('A1', record.company_id.name, title_format)
            sheet.write('G1', 'REQUISICION DE COMPRAS', title_format)

            # Encabezados de la tabla
            headers = ['#ID', 'Producto', 'Descripcion', 'Cta Analitica', 'Unidad', 'Cantidad', 'Empleados', 'UnSoloCustodio']
            row = 2
            for col, header in enumerate(headers):
                sheet.write(row, col, header, header_format)
            row += 1

            # Obtener líneas ordenadas por 'sequence'
            for line in record.line_ids.sorted(key=lambda l: l.sequence):
                analytic_names = []
                if isinstance(line.analytic_distribution, dict):
                    for analytic_id in line.analytic_distribution.keys():
                        analytic = self.env['account.analytic.account'].browse(int(analytic_id))
                        if analytic.exists():
                            analytic_names.append(analytic.name)

                # Escribir la fila
                sheet.write(row, 0, line.id or '')
                sheet.write(row, 1, line.product_id.default_code or '')
                sheet.write(row, 2, line.name or '')
                sheet.write(row, 3, ', '.join(analytic_names))
                sheet.write(row, 4, line.product_uom_id.name if line.product_uom_id else '')
                sheet.write(row, 5, line.product_qty or 0)
                sheet.write(row, 6, ', '.join(line.employees_ids.mapped('identification_id')))
                sheet.write(row, 7, 'Sí' if line.un_solo_custodio else 'No')
                row += 1

            # Guardar archivo
            workbook.close()
            output.seek(0)
            record.file_data = base64.b64encode(output.read())
            output.close()

        # Acción para descargar el archivo
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/file_data/{self.name}.xlsx',
            'target': 'self',
        }

    def button_descargarXXX(self):
        for record in self:
            # Crear el archivo Excel en memoria
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output)
            sheet = workbook.add_worksheet('PurchaseRequest')

            # Formatos
            title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
            header_format = workbook.add_format({'bold': True, 'align': 'left'})
            value_format = workbook.add_format({'align': 'left'})

            # Cabecera principal
            sheet.write('A1', record.company_id.name, title_format)
            sheet.write('G1', 'REQUISICION DE COMPRAS', title_format)

            # Detalles de la cabecera
            sheet.write('A2', 'EMPLEADO:', header_format)

            sheet.write('A3', 'PROVEEDOR:', header_format)

            
            # Espaciado para la tabla
            row = 2
            # Encabezados de la tabla
            headers = ['#ID','Producto','Descripcion', 'CtaAnalitica','Unidad', 'Cantidad','Empleados','UnSoloCustodio']
            for col, header in enumerate(headers):
                sheet.write(row, col, header, header_format)
            row = row + 1
            sum = 0
            for line in record.line_ids:
                sheet.write(row, 0, line.id)
                sheet.write(row, 1, line.product_id.default_code or '')
                sheet.write(row, 2, line.name or '')
                analytic_names = []
                for analytic_id in line.analytic_distribution.keys():
                    analytic = self.env['account.analytic.account'].browse(int(analytic_id))
                    if analytic.exists():
                        analytic_names.append(analytic.name)
                sheet.write(row, 3, ', '.join(analytic_names))
                #sheet.write(row, 3, json.dumps(line.analytic_distribution))
                sheet.write(row, 4, line.product_id.uom_po_id.name or '')
                sheet.write(row, 5, line.product_qty)
                sheet.write(row, 6, ', '.join(line.employees_ids.mapped('identification_id')))
                sheet.write(row, 7, line.un_solo_custodio)
                # if self.env.user.has_group('account_payment_purchase.group_analytic_user'):
                #     sheet.write(row, 8, line.precio_venta)
                # else:
                #     sheet.write(row, 8, 0)
                row += 1
            # Guardar el archivo en memoria
            workbook.close()
            output.seek(0)

            # Convertir el archivo a base64 y guardarlo en el campo
            record.file_data = base64.b64encode(output.read())
            output.close()

        # Retornar acción para descargar el archivo
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/file_data/{self.name}.xlsx',
            'target': 'self',
        }
    
    @api.model
    def _cron_notificar_requisiciones_evaluacion(self):
        today = fields.Date.context_today(self)
        solicitudes = self.search([
            ('state', '=', 'approved'),
            ('date_start', '!=', False),
        ])

        pendientes = []
        for req in solicitudes:
            dias_limite = req.company_id.dias_eval
            if dias_limite <= 0:
                continue

            dias_aprobada = (today - req.date_start).days
            tiene_oc = req.mapped("line_ids.purchase_lines.order_id")

            if dias_aprobada > dias_limite and not tiene_oc:
                pendientes.append((req, dias_aprobada))

        if not pendientes:
            return

        # Construcción del contenido HTML
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        cuerpo_html = """
        <p>Las siguientes requisiciones están aprobadas pero no han sido convertidas en orden de compra:</p>
        <table border="1" cellspacing="0" cellpadding="4" style="border-collapse: collapse; width:100%;">
            <thead style="background-color:#f0f0f0;">
                <tr>
                    <th>Compañía</th>
                    <th>Requisición</th>
                    <th>Fecha de Aprobación</th>
                    <th>Días sin OC</th>
                    <th>Solicitado por</th>
                </tr>
            </thead>
            <tbody>
        """

        for requisicion, dias in pendientes:
            url = f"{base_url}/web#id={requisicion.id}&model=purchase.request&view_type=form"
            compania = requisicion.company_id.name
            fecha_aprob = requisicion.write_date.strftime('%d/%m/%Y') if requisicion.write_date else 'N/A'
            aprobador = requisicion.assigned_to.name or 'N/A'
            solicitante = requisicion.requested_by.name or 'N/A'

            cuerpo_html += f"""
                <tr>
                    <td>{compania}</td>
                    <td><a href="{url}">{requisicion.name}</a></td>
                    <td>{fecha_aprob}</td>
                    <td style="text-align: center;">{dias}</td>
                    <td>{solicitante}</td>
                </tr>
            """

        cuerpo_html += """
            </tbody>
        </table>
        """

        # Usuarios destino
        grupo = self.env.ref("account_payment_purchase.group_pgpp_cambiar").users
        user1 = self.env['res.users'].search([('login', '=', 'mmorquecho@gpsgroup.com.ec')], limit=1)
        user2 = self.env['res.users'].search([('login', '=', 'dpincay@gpsgroup.com.ec')], limit=1)

        all_users = grupo #| user1 | user2
        all_partners = all_users.mapped('partner_id').filtered(lambda p: p.email)

        if not all_partners:
            return
        for req, _ in pendientes:
            if req.requested_by.partner_id not in all_partners:
                all_partners |= req.requested_by.partner_id

        self.env['mail.mail'].create({
            'subject': 'Requisiciones Aprobadas sin Orden de Compra',
            'body_html': cuerpo_html,
            'email_to': ",".join(all_partners.mapped('email')),
            'auto_delete': True,
        }).send()