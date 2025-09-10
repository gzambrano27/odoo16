# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError



class ProductTemplate(models.Model):
    _inherit = 'product.template'

    asset_category_id = fields.Many2one('account.asset.category', string='Asset Type',
                                        company_dependent=True, ondelete="restrict")
    deferred_revenue_category_id = fields.Many2one('account.asset.category', string='Deferred Revenue Type',
                                                   company_dependent=True, ondelete="restrict")

    def _get_asset_accounts(self):
        res = super(ProductTemplate, self)._get_asset_accounts()
        if self.asset_category_id:
            res['stock_input'] = self.property_account_expense_id
        if self.deferred_revenue_category_id:
            res['stock_output'] = self.property_account_income_id
        return res


class ProductCategory(models.Model):
    _inherit = "product.category"

    asset_fixed_control = fields.Boolean(
        help="Applies only if the product will be a control asset, that is, if it will be assigned to employees.",
    )
    asset_fixed_depreciable = fields.Boolean(
        help="Applies only if the product is a depreciable asset, meaning it will lose value over time due to wear, usage, or obsolescence.",
    )

    #validar que si se ha marcado uno de los dos asset_fixed_control o asset_fixed_depreciable no permita que el otro sea marcado
    @api.constrains('asset_fixed_control', 'asset_fixed_depreciable')
    def _check_exclusive_asset_flags(self):
        for record in self:
            if record.asset_fixed_control and record.asset_fixed_depreciable:
                raise ValidationError(
                    "Only one can be selected: 'Control Asset' or 'Depreciable Asset', not both at the same time."
                )

class Product(models.Model):

    _inherit = 'product.template'

    @api.model
    def create(self, vals):
        if vals.get('categ_id'):
            category = self.env['product.category'].browse(vals['categ_id'])
            if category and category.asset_fixed_control and vals.get('tracking') == 'serial' and vals.get('detailed_type') == 'product':
                # Si la categoria es "Activos Fijos Menores", generar un codigo de referencia AFM
                if vals.get('default_code'):
                    sequence = self.env['ir.sequence'].search([('code', '=', 'product.internal.ref')], limit=1)
                    if sequence and sequence.number_next_actual > 1:
                        sequence.sudo().number_next_actual -= 1
                sequence = self.env['ir.sequence'].next_by_code('product.asset.small.code')
                vals['default_code'] = sequence  # Asignar el codigo secuencial al campo 'default_code'
                vals['referencia_company'] = sequence  # Asignar el codigo secuencial al campo 'default_code'
            elif category and category.asset_fixed_depreciable and vals.get('tracking') == 'serial' and vals.get('detailed_type') == 'product':
                # Si el producto es un activo, genera un c�digo de referencia PPE
                if vals.get('default_code'):
                    sequence = self.env['ir.sequence'].search([('code', '=', 'product.internal.ref')], limit=1)
                    if sequence and sequence.number_next_actual > 1:
                        sequence.sudo().number_next_actual -= 1
                sequence = self.env['ir.sequence'].next_by_code('product.asset.code')
                vals['default_code'] = sequence  # Asignar el codigo secuencial al campo 'default_code'
                vals['referencia_company'] = sequence  # Asignar el codigo secuencial al campo 'default_code'
        # Llamar al m�todo 'create' original
        return super(Product, self).create(vals)
