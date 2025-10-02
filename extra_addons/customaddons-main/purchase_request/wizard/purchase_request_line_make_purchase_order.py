# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError,ValidationError
from odoo.tools import get_lang, raise_error
from datetime import timedelta

class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _name = "purchase.request.line.make.purchase.order"
    _description = "Purchase Request Line Make Purchase Order"

    comprador_id = fields.Many2one(
        comodel_name="res.users",
        string="Comprador",
        tracking=True,
        index=True,
        default=lambda self: self.env.uid
    )

    supplier_id = fields.Many2one(
        comodel_name="res.partner",
        string="Supplier",
        required=True,
        context={"res_partner_search_mode": "supplier"},
    )
    item_ids = fields.One2many(
        comodel_name="purchase.request.line.make.purchase.order.item",
        inverse_name="wiz_id",
        string="Items",
    )
    purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Purchase Order",
        domain=[("state", "=", "draft")],
    )
    sync_data_planned = fields.Boolean(
        string="Match existing PO lines by Scheduled Date",
        help=(
            "When checked, PO lines on the selected purchase order are only reused "
            "if the scheduled date matches as well."
        ),
    )
    

    @api.model
    def _prepare_item(self, line):
        # Buscar órdenes de compra relacionadas con la línea
        purchase_lines = self.env['purchase.order.line'].search([
            ('custom_requisition_line_id', '=', line.id)
        ])

        # Evaluar si todas están canceladas
        all_cancelled = all(pol.order_id.state == 'cancel' for pol in purchase_lines)

        if all_cancelled:
            # Permitir recrear la solicitud si las compras previas fueron canceladas
            return {
                "line_id": line.id,
                "request_id": line.request_id.id,
                "product_id": line.product_id.id,
                "product_qty": line.product_qty,
                "name": line.name or line.product_id.name,
                "referencia_anterior_po": line.referencia_anterior_po,
                "product_brand_id": line.product_brand_id.id,
                "product_uom_id": line.product_uom_id.id,
                "un_solo_custodio": line.un_solo_custodio,
                "employees_ids": line.employees_ids.ids,
                "display_type": line.display_type,
                "costo_uni_apu": line.costo_uni_apu,
            }

        # Caso normal: solo permite si aún falta por comprar
        if line.purchased_qty < line.product_qty:
            dif = line.product_qty - line.purchased_qty
            return {
                "line_id": line.id,
                "request_id": line.request_id.id,
                "product_id": line.product_id.id,
                "product_qty": dif,
                "name": line.name or line.product_id.name,
                "referencia_anterior_po": line.referencia_anterior_po,
                "product_brand_id": line.product_brand_id.id,
                "product_uom_id": line.product_uom_id.id,
                "un_solo_custodio": line.un_solo_custodio,
                "employees_ids": line.employees_ids.ids,
                "display_type": line.display_type,
                "costo_uni_apu":line.costo_uni_apu
            }
        else:
            raise UserError(
                _("Ya se ha comprado la cantidad completa para el producto '%s'.") % line.product_id.display_name
            )

    @api.model
    def _check_valid_request_line(self, request_line_ids):
        picking_type = False
        company_id = False

        for line in self.env["purchase.request.line"].browse(request_line_ids):
            #if not self.env.user.has_group('account_payment_purchase.group_purchase_user_registrador') and line.request_id.request_type not in ('consu','service'):
            if not (
                    self.env.user.has_group('purchase.group_purchase_manager') or
                    self.env.user.has_group('account_payment_purchase.group_purchase_user_registrador')
                ):
                raise UserError(_("No tienes permiso para crear una cotizacion de OC!!."))
            if line.request_id.estado_revision=='no revisado' and line.request_id.company_id!=1 and line.request_id.request_type=='product':#excluyo x el momento a Import Blue
                raise UserError(_("No puedes generar una OC si Supply no ha revisado el stock!!."))
            if line.request_id.state == "done":
                raise UserError(_("The purchase has already been completed."))
            if line.request_id.state not in ["approved", "in_progress"]:
                raise UserError(
                    _("Purchase Request %s is not approved or in progress")
                    % line.request_id.name
                )

            if line.purchase_state == "done":
                raise UserError(_("The purchase has already been completed."))

            line_company_id = line.company_id and line.company_id.id or False
            if company_id is not False and line_company_id != company_id:
                raise UserError(_("You have to select lines from the same company."))
            else:
                company_id = line_company_id

            #if line.purchased_qty <= line.product_qty:
            #    raise UserError(_("You have to enter a positive quantity for the following product '%s'.") % line.product_id.default_code)

            line_picking_type = line.request_id.picking_type_id or False
            if not line_picking_type:
                raise UserError(_("You have to enter a Picking Type."))
            if picking_type is not False and line_picking_type != picking_type:
                raise UserError(
                    _("You have to select lines from the same Picking Type.")
                )
            else:
                picking_type = line_picking_type

    @api.model
    def check_group(self, request_lines):
        if len(list(set(request_lines.mapped("request_id.group_id")))) > 1:
            raise UserError(
                _(
                    "You cannot create a single purchase order from "
                    "purchase requests that have different procurement group."
                )
            )

    @api.model
    def get_items(self, request_line_ids):
        request_line_obj = self.env["purchase.request.line"]
        items = []
        request_lines = request_line_obj.browse(request_line_ids)
        self._check_valid_request_line(request_line_ids)
        self.check_group(request_lines)
        lines = request_lines.filtered(lambda l: not l.cancelled)
        lines = lines.sorted(key=lambda l: l.sequence)

        items = []
        for line in lines:
            if line.display_type == 'line_section':
                # línea tipo sección
                items.append([0, 0, {
                    'line_id': line.id,
                    'request_id': line.request_id.id,
                    'name': line.name,
                    'display_type': 'line_section',
                    'product_qty': 0.0,
                    'product_uom_id': False,
                    'keep_description': True,
                }])
            else:
                # línea de producto normal
                items.append([0, 0, self._prepare_item(line)])
        return items

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        active_model = self.env.context.get("active_model", False)
        request_line_ids = []
        if active_model == "purchase.request.line":
            request_line_ids += self.env.context.get("active_ids", [])
        elif active_model == "purchase.request":
            request_ids = self.env.context.get("active_ids", False)
            request_line_ids += (
                self.env[active_model].browse(request_ids).mapped("line_ids")
                .filtered(lambda l: not l.cancelled and (
                    l.display_type == 'line_section' or l.purchased_qty < l.product_qty
                )).ids
            )
            # request_line_ids += (
            #     self.env[active_model].browse(request_ids).mapped("line_ids").filtered(lambda l: not l.cancelled).filtered(lambda l: l.purchased_qty < l.product_qty).ids
            # )
        if not request_line_ids:
            return res
        res["item_ids"] = self.get_items(request_line_ids)
        request_lines = self.env["purchase.request.line"].browse(request_line_ids)
        supplier_ids = request_lines.mapped("supplier_id").ids
        if len(supplier_ids) == 1:
            res["supplier_id"] = supplier_ids[0]
        return res

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin, requested_by, assigned_to, date_planned,request_id,description,rendimiento,equipos,personal_min_equipo,duracion_estimada,tipo_pedido,fiscalizador,tipo_contrato):
        if not self.supplier_id:
            raise UserError(_("Enter a supplier."))
        supplier = self.supplier_id
        userreq = self.env['res.users'].browse(requested_by.id)
        is_admin = userreq.has_group('account_payment_purchase.group_purchase_admin')
        is_presidencia = userreq.has_group('account_payment_purchase.group_purchase_presidencia')
        data = {
            'purchase_request_id':request_id,
            "origin": origin,
            "partner_id": self.supplier_id.id,
            "payment_term_id": self.supplier_id.property_supplier_payment_term_id.id,
            "fiscal_position_id": supplier.property_account_position_id
            and supplier.property_account_position_id.id
            or False,
            "picking_type_id": picking_type.id,
            "company_id": company.id,
            "group_id": group_id.id,
            "solicitante": requested_by.id,
            "user_id": self.comprador_id.id,
            "date_planned": date_planned,
            #'es_admin': True if (requested_by.login =='mmpico@gpsgroup.com.ec' or requested_by.login =='avasconez@gpsgroup.com.ec' or requested_by.login =='aarriola@gpsgroup.com.ec') else False
            #'es_admin': True if (requested_by.login =='mmpico@gpsgroup.com.ec') else False
            'es_admin': is_admin,
            'es_presidencia':is_presidencia,
            'notes':description,
            'rendimiento': rendimiento,
            'equipos': equipos,
            'personal_min_equipo': personal_min_equipo,
            'duracion_estimada': duracion_estimada,
            'tipo_pedido': tipo_pedido,
            'fiscalizador_id': fiscalizador,
            'tipo_contrato': tipo_contrato
        }
        return data

    def create_allocation(self, po_line, pr_line, new_qty, alloc_uom):
        vals = {
            "requested_product_uom_qty": new_qty,
            "product_uom_id": alloc_uom.id,
            "purchase_request_line_id": pr_line.id,
            "purchase_line_id": po_line.id,
        }
        return self.env["purchase.request.allocation"].create(vals)

    @api.model
    def _prepare_purchase_order_line(self, po, item):
        sequence = item.line_id.sequence
        if item.display_type == 'line_section':
            return {
                'order_id': po.id,
                'name': item.name,
                'display_type': 'line_section',
                'sequence': sequence,
                'date_planned': fields.Datetime.now(),
                'product_id': False,
                'product_uom': False,
                'product_qty': 0.0,
                'price_unit': 0.0,
            }
        if not item.product_id:
            raise UserError(_("Please select a product for all lines"))
        product = item.product_id

        # Keep the standard product UOM for purchase order so we should
        # convert the product quantity to this UOM
        qty = item.product_uom_id._compute_quantity(
            item.product_qty, product.uom_po_id or product.uom_id
        )
        # Suggest the supplier min qty as it's done in Odoo core
        min_qty = item.line_id._get_supplier_min_qty(product, po.partner_id)
        qty = max(qty, min_qty)
        date_required = item.line_id.date_required
        if not item.product_id and not item.display_type:
            raise UserError(_("La línea '%s' no tiene producto ni es sección. Revisa su definición.") % item.name)
        return {
            'sequence': sequence,
            "order_id": po.id,
            "product_id": product.id,
            "referencia_anterior_po": item.referencia_anterior_po,
            "product_brand_id": item.product_brand_id.id,
            "product_uom": product.uom_po_id.id or product.uom_id.id,
            "price_unit": 0.0,
            "product_qty": qty,
            "analytic_distribution": item.line_id.analytic_distribution,
            "purchase_request_lines": [(4, item.line_id.id)],
            #"date_planned": po.date_planned,
            "date_planned": item.line_id.date_required or po.date_planned or fields.Datetime.now(),
            "move_dest_ids": [(4, x.id) for x in item.line_id.move_dest_ids],
            "employees_ids": [(6, 0, item.employees_ids.ids)],
            "display_type": item.display_type or False,
            "costo_uni_apu":item.line_id.costo_uni_apu
        }

    @api.model
    def _get_purchase_line_name(self, order, line):
        """Fetch the product name as per supplier settings"""
        product_lang = line.product_id.with_context(
            lang=get_lang(self.env, self.supplier_id.lang).code,
            partner_id=self.supplier_id.id,
            company_id=order.company_id.id,
        )
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += "\n" + product_lang.description_purchase
        return name

    @api.model
    def _get_order_line_search_domain(self, order, item):
        vals = self._prepare_purchase_order_line(order, item)
        name = self._get_purchase_line_name(order, item)
        order_line_data = [
            ("order_id", "=", order.id),
            ("name", "=", name),
            ("product_id", "=", item.product_id.id),
            ("product_uom", "=", vals["product_uom"]),
            ("analytic_distribution", "=?", item.line_id.analytic_distribution),
        ]
        if self.sync_data_planned:
            date_required = item.line_id.date_required
            order_line_data += [
                (
                    "date_planned",
                    "=",
                    datetime(
                        date_required.year, date_required.month, date_required.day
                    ),
                )
            ]
        if not item.product_id:
            order_line_data.append(("name", "=", item.name))
        return order_line_data

    def make_purchase_order(self):
        res = []
        purchase_obj = self.env["purchase.order"]
        po_line_obj = self.env["purchase.order.line"]
        purchase = False

        for item in self.item_ids.sorted(key=lambda l: l.line_id.sequence):
        #for item in self.item_ids:
            line = item.line_id
            if item.product_qty <= 0.0 and item.display_type != 'line_section':
                #raise UserError(_("Enter a positive quantity."))
                raise UserError(_("Enter a positive quantity for the following product '%s'", line.product_id.default_code))
            
            
            if line.product_id.categ_id.asset_fixed_control or line.product_id.categ_id.asset_fixed_depreciable:
                if not (len(item.employees_ids.ids) == int(item.product_qty)):
                    if not item.line_id.un_solo_custodio:
                        raise UserError(_("El producto '%s' es un activo fijo y debe ser asignado a la misma cantidad de empleados.",item.product_id.default_code))
                    else:
                        if (len(item.employees_ids.ids)<1):
                                        raise UserError(_("El producto '%s' es un activo fijo y debe ser asignado al menos un custodio.", item.product_id.default_code))
                employees_prlmpoi = item.employees_ids
                employess_prle = line.employees_ids



                if not all(emp in employess_prle for emp in employees_prlmpoi):
                    raise UserError(
                        _("El Empleado '%s' no se encuentra en la requisicion inicial.", employees_prlmpoi))

                    #VALIDAR QUE LOS EMPLEADOS SELECCIONADOS SEAN LOS MISMOS QUE ESTAN EN LA PURCHASE REQUEST LINE
                    #request_ids = self.env.context.get("active_ids", False)

                    #.filtered(lambda l: not l.cancelled).ids
                    #for employee in item.employees_ids:
                    #    if employee not in line.employees_ids:
                    #        raise UserError(_("El empleado '%s' no esta asignado a la linea de requisición de compra '%s'.", employee.name, line.name))

            if self.purchase_order_id:
                purchase = self.purchase_order_id
            if not purchase:
                po_data = self._prepare_purchase_order(
                    line.request_id.picking_type_id,
                    line.request_id.group_id,
                    line.company_id,
                    line.request_id.name,#origin,
                    line.request_id.requested_by,
                    line.request_id.assigned_to,
                    line.request_id.date_planned + timedelta(days=1),
                    line.request_id.id,
                    line.request_id.description,
                    line.request_id.rendimiento,
                    line.request_id.equipos,
                    line.request_id.personal_min_equipo,
                    line.request_id.duracion_estimada,
                    line.request_id.tipo_pedido,
                    line.request_id.fiscalizador_id.id,
                    line.request_id.tipo_contrato
                )
                    #line.request_id.employees_id.ids
                purchase = purchase_obj.create(po_data)

            # Look for any other PO line in the selected PO with same
            # product and UoM to sum quantities instead of creating a new
            # po line
            domain = self._get_order_line_search_domain(purchase, item)
            available_po_lines = po_line_obj.search(domain)
            new_pr_line = True
            # If Unit of Measure is not set, update from wizard.
            if not line.product_uom_id:
                line.product_uom_id = item.product_uom_id
            # Allocation UoM has to be the same as PR line UoM
            alloc_uom = line.product_uom_id
            wizard_uom = item.product_uom_id
            if available_po_lines and not item.keep_description:
                new_pr_line = False
                po_line = available_po_lines[0]
                po_line.purchase_request_lines = [(4, line.id)]
                po_line.move_dest_ids |= line.move_dest_ids
                po_line_product_uom_qty = po_line.product_uom._compute_quantity(
                    po_line.product_uom_qty, alloc_uom
                )
                wizard_product_uom_qty = wizard_uom._compute_quantity(
                    item.product_qty, alloc_uom
                )
                all_qty = min(po_line_product_uom_qty, wizard_product_uom_qty)
                if item.display_type != 'line_section':
                    self.create_allocation(po_line, line, all_qty, alloc_uom)
            else:
                po_line_data = self._prepare_purchase_order_line(purchase, item)
                if item.keep_description:
                    po_line_data["name"] = item.name
                po_line = po_line_obj.create(po_line_data)
                if not po_line.display_type and po_line.price_unit != 0.0:
                    po_line.price_unit = 0.0
                if not po_line_data.get('display_type') and not po_line_data.get('product_id'):
                    raise UserError("Falta display_type en línea sin producto: %s" % item.name)
                po_line_product_uom_qty = po_line.product_uom._compute_quantity(
                    po_line.product_uom_qty, alloc_uom
                )
                wizard_product_uom_qty = wizard_uom._compute_quantity(
                    item.product_qty, alloc_uom
                )
                all_qty = min(po_line_product_uom_qty, wizard_product_uom_qty)
                if item.display_type != 'line_section':
                    self.create_allocation(po_line, line, all_qty, alloc_uom)
            if item.display_type != 'line_section':
                self._post_process_po_line(item, po_line, new_pr_line)
            res.append(purchase.id)

        purchase_requests = self.item_ids.mapped("request_id")
        purchase_requests.button_in_progress()
        return {
            "domain": [("id", "in", res)],
            "name": _("RFQ"),
            "view_mode": "tree,form",
            "res_model": "purchase.order",
            "view_id": False,
            "context": False,
            "type": "ir.actions.act_window",
        }

    def _post_process_po_line(self, item, po_line, new_pr_line):
        self.ensure_one()
        line = item.line_id
        # TODO: Check propagate_uom compatibility:
        new_qty = self.env["purchase.request.line"]._calc_new_qty(
            line, po_line=po_line, new_pr_line=new_pr_line
        )
        po_line.product_qty = new_qty
        # The quantity update triggers a compute method that alters the
        # unit price (which is what we want, to honor graduate pricing)
        # but also the scheduled date which is what we don't want.
        date_required = line.date_required
        po_line.date_planned = po_line.date_planned
        

class PurchaseRequestLineMakePurchaseOrderItem(models.TransientModel):
    _name = "purchase.request.line.make.purchase.order.item"
    _description = "Purchase Request Line Make Purchase Order Item"

    wiz_id = fields.Many2one(
        comodel_name="purchase.request.line.make.purchase.order",
        string="Wizard",
        required=True,
        ondelete="cascade",
        readonly=True,
    )
    line_id = fields.Many2one(
        comodel_name="purchase.request.line", string="Purchase Request Line"
    )
    request_id = fields.Many2one(
        comodel_name="purchase.request",
        related="line_id.request_id",
        string="Purchase Request",
        readonly=False,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        related="line_id.product_id",
        readonly=False,
    )
    name = fields.Char(string="Description", required=True)

    referencia_anterior_po = fields.Char(related='product_id.referencia_anterior', string='Referencia Anterior')
    product_brand_id = fields.Many2one("product.brand",string="Marca",help="Select a brand for this product",store=True)


    product_qty = fields.Float(
        string="Quantity to purchase", digits="Product Unit of Measure"
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom", string="UoM", required=False
    )
    keep_description = fields.Boolean(
        string="Copy descriptions to new PO",
        help="Set false if you want to keep the "
        "descriptions provided in the "
        "wizard in the new PO.",
        default = True
    )
    employees_ids = fields.Many2many(
        comodel_name="hr.employee",
        # relation="purchase_request_employee_rel",
        # column1="purchase_request_line_id",
        # column2="employee_id",
        string="Employees",
    )

    un_solo_custodio = fields.Boolean('Un Custodio?')
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ], string="Display Type")
    costo_uni_apu = fields.Float('Costo U. Apu', digits=(16,4))

    @api.onchange("product_id")
    def onchange_product_id(self):
        if self.product_id:
            allowed_prod_ids = self.line_id.request_id.line_ids.filtered(lambda l: not l.cancelled).filtered(lambda l: l.purchased_qty < l.product_qty).mapped('product_id').ids
            if self.product_id.id not in allowed_prod_ids:
                raise UserError(_("El producto '%s' no está entre las líneas de la solicitud.",self.product_id.default_code))
            if not self.keep_description:
                name = self.product_id.name
            code = self.product_id.code
            sup_info_id = self.env["product.supplierinfo"].search(
                [
                    "|",
                    ("product_id", "=", self.product_id.id),
                    ("product_tmpl_id", "=", self.product_id.product_tmpl_id.id),
                    ("partner_id", "=", self.wiz_id.supplier_id.id),
                ]
            )
            if sup_info_id:
                p_code = sup_info_id[0].product_code
                p_name = sup_info_id[0].product_name
                name = "[{}] {}".format(
                    p_code if p_code else code, p_name if p_name else name
                )
            else:
                if code:
                    name = "[{}] {}".format(
                        code, self.name if self.keep_description else name
                    )
            if self.product_id.description_purchase and not self.keep_description:
                name += "\n" + self.product_id.description_purchase
            self.product_uom_id = self.product_id.uom_id.id
            if name:
                self.name = name

    @api.onchange("product_qty")
    def onchange_product_qty(self):
        if (self.product_qty<=0) or (self.product_qty is None) or (self.product_qty > (self.line_id.product_qty - self.line_id.purchased_qty)):
            self.product_qty = (self.line_id.product_qty - self.line_id.purchased_qty)
            #raise UserError(_("La cantidad del producto '%s' no puede ir con valor 0.",self.product_id.default_code))
            return {'warning': {
                'title': _("Cantidad inválida"),
                'message': _("La cantidad del producto '%s' no puede ser mayor ni menor a la cantidad faltante.") % (
                    self.product_id.default_code,
                ),
            }
            }



