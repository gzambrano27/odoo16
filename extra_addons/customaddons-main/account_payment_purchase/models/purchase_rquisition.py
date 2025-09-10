from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
import json
from datetime import datetime

class MaterialPurchaseRequisition(models.Model):
    _inherit = "material.purchase.requisition"

    payment_term_id = fields.Many2one('account.payment.term', 'Plazos de Pago', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    date_advance_payment=fields.Date(string="Fecha de Primer Anticipo",tracking=True)
    requisition_line_ids = fields.One2many(
        "material.purchase.requisition.line",
        "requisition_id",
        string="Purchase Requisitions Line",
        copy=False,
        domain= [('display_type', '=', False)]
    )
    requisition_line_with_sectionnote_ids = fields.One2many(
        comodel_name="material.purchase.requisition.line",
        inverse_name="requisition_id",
        string="Lines With Sections & Notes",
        copy=True,
    )
    

    @api.constrains('requisition_line_ids')
    def _check_analytic_account_for_service_products(self):
        """
        Validar que si existe un producto de tipo 'producto' en las líneas de la requisición,
        se debe ingresar una cuenta analítica.
        """
        for requisition in self:
            has_service_product = False
            for line in requisition.requisition_line_ids:
                if line.product_id.detailed_type == 'product':
                    has_service_product = True
            # Opcional: si se requiere que exista cuenta analítica en la requisición principal también
            if has_service_product and not self.analytic_account_id:
                raise ValidationError(
                    _("Debe ingresar una cuenta analítica en la requisición si incluye productos de tipo Almacenable.")
                )
            
    def requisition_confirm(self):
        for requisition in self:
            has_service_product = False
            for line in requisition.requisition_line_ids:
                if line.product_id.detailed_type == 'product':
                    has_service_product = True
            # Opcional: si se requiere que exista cuenta analítica en la requisición principal también
            if has_service_product and not self.analytic_account_id:
                raise ValidationError(
                    _("Debe ingresar una cuenta analítica en la requisición si incluye productos de tipo Almacenable.")
                )
        return super(MaterialPurchaseRequisition, self).requisition_confirm()
    
    def _create_purchase_orders(self, partner, line, po_dict):
        purchase_obj = self.env['purchase.order']
        purchase_line_obj = self.env['purchase.order.line']
        #picking_type = self.env['stock.picking.type'].search([('default_location_dest_id', '=', self.dest_location_id.id)], limit=1)
        picking_type = self.env['stock.picking.type'].search([('barcode', 'like',  f"%RECEIP%"),('warehouse_id','=',self.dest_location_id.warehouse_id.id),('code','=','incoming')], limit=1)
        is_admin = False
        is_presidencia = False
        if partner not in po_dict:
            is_admin = self.create_uid.has_group('account_payment_purchase.group_purchase_admin')
            is_presidencia = self.create_uid.has_group('account_payment_purchase.group_purchase_presidencia')
            po_vals = {
                "partner_id": partner.id,
                "currency_id": self.env.user.company_id.currency_id.id,
                "date_order": fields.Date.today(),
                "company_id": self.company_id.id,
                "custom_requisition_id": self.id,
                "origin": self.name,
                "picking_type_id": picking_type.id,
                "solicitante": self.requisiton_responsible_id.user_id.id,
                'analytic_distribution': {str(self.analytic_account_id.id): 100}  if self.analytic_account_id else False,
                'payment_term_id':self.payment_term_id.id,
                'notes':self.reason,
                'date_advance_payment':self.date_advance_payment,
                #'es_admin': True if (self.create_uid.login =='mmpico@gpsgroup.com.ec' or self.create_uid.login =='avasconez@gpsgroup.com.ec' or self.create_uid.login =='aarriola@gpsgroup.com.ec') else False
                'es_admin': is_admin,
                'es_presidencia':is_presidencia
            }
            purchase_order = purchase_obj.create(po_vals)
            po_dict.update({partner: purchase_order})
            po_line_vals = self._prepare_po_line(line, purchase_order)
            purchase_line_obj.sudo().create(po_line_vals)
        else:
            purchase_order = po_dict.get(partner)
            po_line_vals = self._prepare_po_line(line, purchase_order)
            purchase_line_obj.sudo().create(po_line_vals)

    @api.model
    def _prepare_po_line(self, line=False, purchase_order=False):
        
        if line.display_type=='line_section':
            po_line_vals = {
            'product_id': None,
            'name': line.name,
            'product_qty': 0,
            'product_uom': None,
            'date_planned': None,
            'price_unit': 0,
            'order_id': purchase_order.id,
            'custom_requisition_line_id': line.id,
            'price_unit': 0,
            'rubro': None,
            'precio_venta': 0,
            'display_type':line.display_type,
            }
        else:
            seller = line.product_id._select_seller(
            partner_id=self._context.get('partner_id'),
            quantity=line.qty,
            date=purchase_order.date_order and purchase_order.date_order.date(),
            uom_id=line.uom
            )
            po_line_vals = {
                'product_id': line.product_id.id,
                'product_qty': line.qty,
                'product_uom': line.uom.id,
                'date_planned': fields.Date.today(),
                # 'price_unit': line.product_id.standard_price,
                'price_unit': seller.price or line.product_id.standard_price or 0.0,
                'order_id': purchase_order.id,
                # 'account_analytic_id': self.analytic_account_id.id,
                #'analytic_distribution': {line.analytic_account_id.id: 100} if line.analytic_account_id else False,
                'custom_requisition_line_id': line.id,
                'name': line.name if line.name else line.description,
                'price_unit': line.price_unit,
                'rubro': line.rubro,
                'precio_venta': line.precio_venta,
            }
        # Si la línea de requisición tiene una cuenta analítica, úsala; de lo contrario, toma la de la cabecera
        if line.analytic_account_id:
            po_line_vals['analytic_distribution'] = {str(line.analytic_account_id.id): 100}
        elif purchase_order.analytic_distribution:
            po_line_vals['analytic_distribution'] = purchase_order.analytic_distribution
        else:
            po_line_vals['analytic_distribution'] = False  # Ninguna cuenta analítica disponible
        return po_line_vals

class MaterialPurchaseRequisitionLine(models.Model):
    _inherit = 'material.purchase.requisition.line'
    _order = "requisition_id, sequence, id"

    product_type = fields.Selection(
        related='product_id.detailed_type', 
        string="Product Type", 
        store=True
    )
    price_unit = fields.Float('Precio')
    rubro = fields.Char('Rubro')
    precio_venta = fields.Float('Precio de Venta')
    company_id = fields.Many2one(
        'res.company', 
        string="Compañía", 
        related='requisition_id.company_id', 
        store=True, 
        readonly=True
    )
    analytic_account_id = fields.Many2one(
    'account.analytic.account', 
    'Cuenta Analitica', 
    domain="[('company_id', '=', parent.company_id)]"
    )
    display_type = fields.Selection([
        ('line_section', "Sección"),
        ('line_note', "Nota"),
    ], string="Tipo de Línea", default = False, help="Define si esta línea es una sección o una nota.")
    name = fields.Char(string="Título de la Sección", help="Nombre de la sección si la línea es de tipo 'Sección' o 'Nota'.")
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=False,
    )
    uom = fields.Many2one(
        'uom.uom',#product.uom in odoo11
        string='Unit of Measure',
        required=False,
    )
    description = fields.Char(
        string='Description',
        required=False,
    )
    qty = fields.Float(
        string='Quantity',
        default=1,
        required=False,
    )
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(
        string='Description',
        required=False,
    )

    _sql_constraints = [
            ('non_accountable_null_fields',
                "CHECK(display_type IS NULL OR (product_id IS NULL AND product_uom_id IS NULL))",
                "Forbidden values on non-accountable purchase order line"),
            ('accountable_required_fields',
                "CHECK(display_type IS NOT NULL OR (product_id IS NOT NULL AND product_uom_id IS NOT NULL))",
                "Missing required fields on accountable purchase order line."),
        ]

    @api.onchange('product_id')
    def onchange_product_id(self):
        for rec in self:
            rec.description = rec.product_id.display_name
            rec.name = rec.product_id.display_name
            rec.uom = rec.product_id.uom_id.id

    def _prepare_add_missing_fields(self, vals):
        """Completa valores faltantes en la línea de requisición"""
        defaults = {
            "qty": vals.get("qty", 1),
            "uom": vals.get("uom") or self.env.ref("uom.product_uom_unit").id,
            "price_unit": vals.get("price_unit", 0.0),
            "description": vals.get("description", "Descripción por defecto"),
        }
        vals.update(defaults)
        return vals
    
    @api.model
    def create(self, vals_list):
        """ Ajusta la secuencia para que cada nueva línea tenga un número único """
        if isinstance(vals_list, dict):
            vals_list = [vals_list]  # Convertir en lista si es un solo diccionario

        for values in vals_list:
            if 'sequence' not in values or values['sequence'] == 10:
                values['sequence'] = self._get_next_sequence(values.get('requisition_id'))

        return super(MaterialPurchaseRequisitionLine, self).create(vals_list)

    def _get_next_sequence(self, requisition_id):
        """ Busca la siguiente secuencia disponible para la requisición """
        last_line = self.search([('requisition_id', '=', requisition_id)], order="sequence desc", limit=1)
        return last_line.sequence + 1 if last_line else 10

    @api.model
    def search(self, args, **kwargs):
        """Elimina el filtro oculto que impide mostrar `line_section` y `line_note` en la vista."""
        print("ANTES DE FILTRAR ARGS:", args)  # 🔹 Depuración antes de modificar los argumentos

        # Si existe el filtro ('display_type', '=', False), lo eliminamos
        new_args = [arg for arg in args if arg != ('display_type', '=', False)]

        # Asegurar que `line_section` y `line_note` sean visibles en la búsqueda
        new_args.append(('display_type', 'in', [False, 'line_section', 'line_note']))

        print("DESPUÉS DE FILTRAR ARGS:", new_args)  # 🔹 Verifica que los filtros han cambiado
        return super(MaterialPurchaseRequisitionLine, self).search(new_args, **kwargs)
    
    @api.constrains('product_id')
    def _check_only_service_products(self):
        for line in self:
            if line.product_id and line.product_id.detailed_type != 'service':
                raise ValidationError(_("Solo se pueden agregar productos de tipo Servicio en las líneas de requisición de servicios."))