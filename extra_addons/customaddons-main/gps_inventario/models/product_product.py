# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from odoo.exceptions import ValidationError,UserError
from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit="product.product"

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args = []
        search_ids = None
        if name:
            search_ids = self.search([('default_code', operator, name)] + args,
                                     limit=limit)
        ###implementar aqui el cambio

        ###fin de implementacion
        if not search_ids:
            search_ids = self.search([('name', operator, name)] + args, limit=limit)
        return (search_ids is not None) and search_ids.name_get() or []

    ultima_fecha_compra = fields.Date(
        string="Ultima Fecha de Compra",
        compute='_compute_ultima_fecha_compra',
        store=True
    )

    ultima_fecha_venta = fields.Date(
        string="Ultima Fecha de Venta",
        compute='_compute_ultima_fecha_venta',
        store=True
    )

    purchase_line_ids = fields.One2many(
        'purchase.order.line', 'product_id', string="Lineas de Compra"
    )

    sale_order_line_ids = fields.One2many(
        'sale.order.line', 'product_id', string="Lineas de Venta"
    )

    @api.depends('purchase_line_ids')
    def _compute_ultima_fecha_compra(self):
        for product in self:
            po_lines = product.purchase_line_ids.filtered(
                lambda l: l.order_id.state in ['purchase', 'done']
            )
            if po_lines:
                product.ultima_fecha_compra = max(po_lines.mapped('date_planned'))
            else:
                product.ultima_fecha_compra = False

    @api.depends('sale_order_line_ids')
    def _compute_ultima_fecha_venta(self):
        for product in self:
            so_lines = product.sale_order_line_ids.filtered(
                lambda l: l.order_id.state in ['sale', 'done']
            )
            if so_lines:
                product.ultima_fecha_venta = max(so_lines.mapped('order_id.date_order'))
            else:
                product.ultima_fecha_venta = False




class ProductTemplate(models.Model):
    _inherit="product.template"

    #detailed_type = fields.Selection(company_dependent=True)

    @api.depends('qty_available')
    def _compute_can_edit_categ(self):
        DEC=2
        for brw_each in self:
            can_edit_categ=not (round(brw_each.qty_available,DEC)!=0.00)
            brw_each.can_edit_categ=can_edit_categ

    can_edit_categ=fields.Boolean(string="Puede editar categoria",store=False,default=True,compute="_compute_can_edit_categ")