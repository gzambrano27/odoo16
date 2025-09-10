# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models,api,_
from odoo.exceptions import ValidationError
from datetime import datetime

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    required_advance_payment=fields.Boolean(compute="_compute_required_advance_payment",store=True,readonly=True,string="Requiere Anticipo",default=False)
    date_advance_payment=fields.Date(string="Fecha de Primer Anticipo",tracking=True)
    date_advance_first_payment = fields.Date(string="Fecha de Primer Anticipo Original", tracking=True)
    payment_term_id=fields.Many2one("account.payment.term",tracking=True,string="Condiciones de pago")

    type_guarantee_ids = fields.Many2many(
        comodel_name='guarantee.order',
        relation='purchase_order_guarantee_rel',
        string='Type of Guarantee',
    )

    analytic_account_names = fields.Char(
        string='Cuentas Analíticas',
        compute='_compute_analytic_account_names',
        store=True
    )
    
    def copy(self, default=None):
        raise ValidationError("No puedes duplicar órdenes de compra.")

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

    def button_confirm(self, **kwargs):
        result = super(PurchaseOrder, self).button_confirm()
        fecha_limite = datetime(datetime.today().year, 11, 1)
        for order in self:
            if order.create_date and order.create_date >= fecha_limite and order.amount_untaxed >= 5000 and not order.type_guarantee_ids:
            #if order.amount_untaxed >= 5000 and not order.type_guarantee_ids:
                raise ValidationError(
                    _("Para aprobar la Orden de Compra %s, debe definir primero el tipo de garantía a aplicar.") % order.name
                    )
        return result
        
    @api.onchange('company_id','payment_term_id','payment_term_id.required_advance_payment','date_order')
    @api.depends('company_id','payment_term_id','payment_term_id.required_advance_payment','date_order')
    def _compute_required_advance_payment(self):
        for brw_each in self:
            required_advance_payment = False
            if brw_each.payment_term_id:
                if brw_each.payment_term_id.required_advance_payment:
                    desde_anticipo = self.env['ir.config_parameter'].sudo().get_param('param.date.from.anticipo.purchase.order', '2030-01-01')
                    if desde_anticipo:
                        fecha_anticipo = datetime.strptime(desde_anticipo, '%Y-%m-%d').date()
                        required_advance_payment=(brw_each.date_order and brw_each.date_order.date()>=fecha_anticipo)
            brw_each.required_advance_payment=required_advance_payment
            
     

    @api.constrains('state','payment_term_id')
    def validate_state_advance_payment(self ):
        for brw_each in self:
            if brw_each.required_advance_payment:
                if not brw_each.date_advance_payment or brw_each.date_advance_payment is None:
                    raise ValidationError(_("Para aprobar la oc %s debes definir primero la fecha del primer anticipo") % (brw_each.name,))

    
    def button_approve(self, force=False):
        res = super().button_approve(force)
        fecha_limite = datetime(datetime.today().year, 11, 1)
        for purchase_order in self.sudo():
            if purchase_order.create_date and purchase_order.create_date >= fecha_limite and purchase_order.amount_untaxed >= 5000 and not purchase_order.type_guarantee_ids:
            #if purchase_order.amount_untaxed >= 5000 and not purchase_order.type_guarantee_ids:
                raise ValidationError(
                    _("Para aprobar la Orden de Compra %s, debe definir primero el tipo de garantía a aplicar.") % purchase_order.name
                )
        return res

class GuaranteeOrder(models.Model):
    _name = "guarantee.order"
    _description = "Guarantee Order"

    name = fields.Char("Name of Guarantee", required=True)
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
    insured_value = fields.Char("Insured Value")
    type_of_contract = fields.Char("Type of Contract")
    validity = fields.Char("Validity")
    
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    analytic_account_names = fields.Char(
        string='Cuentas Analíticas',
        compute='_compute_analytic_account_names',
        store=True
    )

    referencia_anterior = fields.Char(string="Referencia Anterior", related='product_id.referencia_anterior',
            store=True,
            readonly=True
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

    
        